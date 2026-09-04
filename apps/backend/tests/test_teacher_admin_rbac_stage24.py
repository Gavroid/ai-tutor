"""Stage 24: teacher/admin RBAC boundary regression tests."""
from __future__ import annotations

import pytest
from app.auth.security import hash_password
from app.db.session import Base, SessionLocal, engine, get_db
from app.main import app
from app.subjects.models import LearningMaterial, Topic
from app.subjects.scripts_seed_runner import seed_for_tests
from app.teacher.schemas import MaterialContent
from app.users.models import Role, User
from fastapi.testclient import TestClient


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    engine.dispose()
    Base.metadata.create_all(engine)

    with SessionLocal() as db:
        users = [
            User(email="student@example.com", password_hash=hash_password("strongpass1"), display_name="Student", role=Role.STUDENT),
            User(email="parent@example.com", password_hash=hash_password("strongpass1"), display_name="Parent", role=Role.PARENT),
            User(email="teacher1@example.com", password_hash=hash_password("strongpass1"), display_name="Teacher 1", role=Role.TEACHER),
            User(email="teacher2@example.com", password_hash=hash_password("strongpass1"), display_name="Teacher 2", role=Role.TEACHER),
            User(email="admin@example.com", password_hash=hash_password("strongpass1"), display_name="Admin", role=Role.ADMIN),
        ]
        db.add_all(users)
        db.flush()
        student, parent, teacher1, teacher2, admin = users
        seed_for_tests(db, reset=False)
        topic = db.query(Topic).order_by(Topic.id).first()
        assert topic is not None
        content = MaterialContent(title="Private teacher draft", purpose="Teacher-only draft").model_dump_json()
        own_material = LearningMaterial(
            topic_id=topic.id,
            title="Teacher 1 draft",
            content=content,
            status="ai_generated",
            generated_by=teacher1.id,
            source_type="topic",
        )
        other_material = LearningMaterial(
            topic_id=topic.id,
            title="Teacher 2 unpublished draft",
            content=content,
            status="ai_generated",
            generated_by=teacher2.id,
            source_type="topic",
        )
        published_other = LearningMaterial(
            topic_id=topic.id,
            title="Teacher 2 published library item",
            content=content,
            status="published",
            generated_by=teacher2.id,
            source_type="topic",
        )
        db.add_all([own_material, other_material, published_other])
        db.commit()
        db.refresh(own_material)
        db.refresh(other_material)
        db.refresh(published_other)
        ids = {
            "topic_id": topic.id,
            "own_material_id": own_material.id,
            "other_material_id": other_material.id,
            "published_other_id": published_other.id,
        }

    def _gen():
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _gen
    with TestClient(app) as test_client:
        for key, value in ids.items():
            setattr(test_client, key, value)
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


def _token(client: TestClient, email: str) -> str:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": "strongpass1"})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_student_and_parent_cannot_access_teacher_endpoints(client):
    student = _token(client, "student@example.com")
    parent = _token(client, "parent@example.com")
    teacher_paths = [
        ("GET", "/api/v1/teacher/topics/readiness", None),
        ("GET", "/api/v1/teacher/materials", None),
        ("GET", f"/api/v1/teacher/materials/{client.own_material_id}", None),
        ("POST", "/api/v1/teacher/materials/bulk-approve", {"material_ids": [client.own_material_id]}),
        ("POST", f"/api/v1/teacher/materials/{client.own_material_id}/approve", None),
        ("POST", f"/api/v1/teacher/materials/{client.own_material_id}/quality-status", {"status": "blocked"}),
        ("POST", f"/api/v1/teacher/rag/rebuild-topic/{client.topic_id}", None),
    ]

    for token in [student, parent]:
        for method, path, payload in teacher_paths:
            response = client.request(method, path, headers=_auth(token), json=payload)
            assert response.status_code == 403, f"{method} {path}: {response.status_code} {response.text}"


def test_student_parent_and_teacher_cannot_access_admin_endpoints(client):
    student = _token(client, "student@example.com")
    parent = _token(client, "parent@example.com")
    teacher = _token(client, "teacher1@example.com")
    admin_paths = [
        ("GET", "/api/v1/admin/audit-log"),
        ("GET", "/api/v1/admin/audit-log/count"),
        ("GET", "/api/v1/admin/audit-log/verify"),
        ("GET", "/api/v1/admin/audit-log/export"),
        ("GET", "/api/v1/admin/users"),
        ("GET", "/api/v1/admin/stats"),
        ("GET", "/api/v1/admin/ops/status"),
        ("GET", "/api/v1/admin/realtime/snapshot"),
        ("GET", "/api/v1/admin/ai-kill-switch"),
    ]

    for token in [student, parent, teacher]:
        for method, path in admin_paths:
            response = client.request(method, path, headers=_auth(token))
            assert response.status_code == 403, f"{method} {path}: {response.status_code} {response.text}"


def test_teacher_cannot_mutate_or_view_other_unpublished_material(client):
    teacher1 = _token(client, "teacher1@example.com")
    other_id = client.other_material_id

    forbidden_requests = [
        ("GET", f"/api/v1/teacher/materials/{other_id}", None),
        ("PATCH", f"/api/v1/teacher/materials/{other_id}", {"title": "stolen"}),
        ("POST", f"/api/v1/teacher/materials/{other_id}/approve", None),
        ("POST", f"/api/v1/teacher/materials/{other_id}/quality-status", {"status": "blocked"}),
        ("POST", f"/api/v1/teacher/materials/{other_id}/publish", None),
        ("POST", f"/api/v1/teacher/materials/{other_id}/unpublish", None),
        ("DELETE", f"/api/v1/teacher/materials/{other_id}", None),
    ]

    for method, path, payload in forbidden_requests:
        response = client.request(method, path, headers=_auth(teacher1), json=payload)
        assert response.status_code == 403, f"{method} {path}: {response.status_code} {response.text}"


def test_teacher_bulk_approve_reports_forbidden_for_other_teacher_material(client):
    teacher1 = _token(client, "teacher1@example.com")

    response = client.post(
        "/api/v1/teacher/materials/bulk-approve",
        headers=_auth(teacher1),
        json={"material_ids": [client.own_material_id, client.other_material_id]},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["approved"] == [client.own_material_id]
    assert body["failed"] == [{"id": str(client.other_material_id), "reason": "forbidden"}]


def test_teacher_can_view_but_not_mutate_other_published_library_item(client):
    teacher1 = _token(client, "teacher1@example.com")
    published_id = client.published_other_id

    view = client.get(f"/api/v1/teacher/materials/{published_id}", headers=_auth(teacher1))
    assert view.status_code == 200, view.text

    for method, path, payload in [
        ("PATCH", f"/api/v1/teacher/materials/{published_id}", {"title": "bad"}),
        ("POST", f"/api/v1/teacher/materials/{published_id}/quality-status", {"status": "blocked"}),
        ("POST", f"/api/v1/teacher/materials/{published_id}/unpublish", None),
        ("DELETE", f"/api/v1/teacher/materials/{published_id}", None),
    ]:
        response = client.request(method, path, headers=_auth(teacher1), json=payload)
        assert response.status_code == 403, f"{method} {path}: {response.status_code} {response.text}"


def test_admin_can_access_admin_and_teacher_boundaries(client):
    admin = _token(client, "admin@example.com")

    assert client.get("/api/v1/admin/audit-log", headers=_auth(admin)).status_code == 200
    assert client.get("/api/v1/admin/users", headers=_auth(admin)).status_code == 200
    assert client.get("/api/v1/admin/stats", headers=_auth(admin)).status_code == 200
    assert client.get("/api/v1/admin/realtime/snapshot", headers=_auth(admin)).status_code == 200

    other = client.patch(
        f"/api/v1/teacher/materials/{client.other_material_id}",
        headers=_auth(admin),
        json={"title": "Admin-reviewed title"},
    )
    assert other.status_code == 200, other.text
    assert other.json()["title"] == "Admin-reviewed title"
