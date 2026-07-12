"""Sprint 1.1 — расширенные тесты RBAC.

Проверяет, что новая зависимость require_role корректно блокирует
неподходящие роли на всех admin/teacher/parent/student endpoints.
"""
from __future__ import annotations

import os

os.environ["APP_SECRET_KEY"] = "test-secret-key-for-pytest-only-1234567890"
os.environ["APP_ENV"] = "development"
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["CORS_ORIGINS"] = "http://localhost:3000"
os.environ["AI_API_KEY"] = "mock-key-for-tests"
os.environ["UPLOAD_DIR"] = "/tmp/ai-tutor-test-uploads"

import pytest
from fastapi.testclient import TestClient

from app.db.session import Base, SessionLocal, engine, get_db
from app.main import app
from app.users import service as user_service
from app.users.schemas import UserCreate


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    engine.dispose()
    Base.metadata.create_all(engine)

    from app.auth.security import hash_password
    from app.users.models import Role as UserRole, User

    s = SessionLocal()
    try:
        # Admin создаётся напрямую — саморегистрация admin запрещена.
        admin = User(
            email="admin@example.com",
            password_hash=hash_password("strongpass1"),
            display_name="Admin",
            role=UserRole.ADMIN,
        )
        s.add(admin)

        user_service.register_user(
            s,
            UserCreate(
                email="teacher@example.com",
                password="strongpass1",
                display_name="Учитель",
                role="teacher",
            ),
        )
        user_service.register_user(
            s,
            UserCreate(
                email="mom@example.com",
                password="strongpass1",
                display_name="Мама",
                role="parent",
            ),
        )
        user_service.register_user(
            s,
            UserCreate(
                email="kid@example.com",
                password="strongpass1",
                display_name="Кирилл",
                role="student",
                grade=7,
            ),
        )
        # Один topic для теста materials/upload
        from app.subjects.scripts_seed_runner import seed_for_tests

        seed_for_tests(s, reset=False)
        from app.subjects.models import Topic

        topic = s.query(Topic).first()
        if topic is None:
            # fallback: создать section+topic вручную
            from app.subjects.models import Section

            from app.subjects.curriculum_7_class import CURRICULUM

            # первый subject + первый topic
            subj_data = next(iter(CURRICULUM.values()))
            from app.subjects.models import Subject

            subj = Subject(
                code="math",
                name=subj_data.get("name", "Математика"),
                recommended_grade=7,
            )
            s.add(subj)
            s.flush()
            sect = Section(
                subject_id=subj.id,
                code="algebra",
                name="Алгебра",
                order_index=1,
            )
            s.add(sect)
            s.flush()
            topic = Topic(
                section_id=sect.id,
                name="Линейные уравнения",
                order_index=1,
            )
            s.add(topic)
            s.commit()
            s.refresh(topic)
        topic_id = topic.id
    finally:
        s.close()

    def _gen():
        s = SessionLocal()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = _gen
    with TestClient(app) as c:
        c.topic_id = topic_id
        yield c
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


def _token(c: TestClient, email: str) -> str:
    r = c.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "strongpass1"},
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ============================================================
# ADMIN endpoints — только admin
# ============================================================

def test_admin_audit_log_blocks_student(client):
    kid = _token(client, "kid@example.com")
    r = client.get("/api/v1/admin/audit-log", headers=_h(kid))
    assert r.status_code == 403


def test_admin_audit_log_blocks_teacher(client):
    teacher = _token(client, "teacher@example.com")
    r = client.get("/api/v1/admin/audit-log", headers=_h(teacher))
    assert r.status_code == 403


def test_admin_audit_log_blocks_parent(client):
    mom = _token(client, "mom@example.com")
    r = client.get("/api/v1/admin/audit-log", headers=_h(mom))
    assert r.status_code == 403


def test_admin_audit_log_allows_admin(client):
    admin = _token(client, "admin@example.com")
    r = client.get("/api/v1/admin/audit-log", headers=_h(admin))
    assert r.status_code == 200


def test_admin_users_blocks_student(client):
    kid = _token(client, "kid@example.com")
    r = client.get("/api/v1/admin/users", headers=_h(kid))
    assert r.status_code == 403


def test_admin_stats_blocks_teacher(client):
    teacher = _token(client, "teacher@example.com")
    r = client.get("/api/v1/admin/stats", headers=_h(teacher))
    assert r.status_code == 403


def test_admin_stats_allows_admin(client):
    admin = _token(client, "admin@example.com")
    r = client.get("/api/v1/admin/stats", headers=_h(admin))
    assert r.status_code == 200


def test_admin_endpoint_requires_auth():
    """Без токена — 401 (не 403)."""
    Base.metadata.drop_all(engine)
    engine.dispose()
    Base.metadata.create_all(engine)
    try:
        with TestClient(app) as c:
            r = c.get("/api/v1/admin/audit-log")
            assert r.status_code == 401
    finally:
        Base.metadata.drop_all(engine)


def test_admin_endpoint_rejects_invalid_token():
    """С битым токеном — 401."""
    Base.metadata.drop_all(engine)
    engine.dispose()
    Base.metadata.create_all(engine)
    try:
        with TestClient(app) as c:
            r = c.get(
                "/api/v1/admin/audit-log",
                headers={"Authorization": "Bearer not-a-real-jwt"},
            )
            assert r.status_code == 401
    finally:
        Base.metadata.drop_all(engine)


# ============================================================
# TEACHER endpoints — teacher или admin
# ============================================================

def test_teacher_material_upload_blocks_student(client):
    kid = _token(client, "kid@example.com")
    files = {"file": ("test.txt", b"hello", "text/plain")}
    data = {"topic_id": str(client.topic_id)}
    r = client.post(
        "/api/v1/materials/upload",
        files=files,
        data=data,
        headers=_h(kid),
    )
    assert r.status_code == 403


def test_teacher_material_upload_blocks_parent(client):
    mom = _token(client, "mom@example.com")
    files = {"file": ("test.txt", b"hello", "text/plain")}
    data = {"topic_id": str(client.topic_id)}
    r = client.post(
        "/api/v1/materials/upload",
        files=files,
        data=data,
        headers=_h(mom),
    )
    assert r.status_code == 403


def test_teacher_material_upload_allows_teacher(client):
    teacher = _token(client, "teacher@example.com")
    files = {"file": ("test.txt", b"hello", "text/plain")}
    data = {"topic_id": str(client.topic_id)}
    r = client.post(
        "/api/v1/materials/upload",
        files=files,
        data=data,
        headers=_h(teacher),
    )
    # 200 или 201 — главное, что не 403
    assert r.status_code in (200, 201), r.text


def test_teacher_material_upload_allows_admin(client):
    admin = _token(client, "admin@example.com")
    files = {"file": ("test.txt", b"hello", "text/plain")}
    data = {"topic_id": str(client.topic_id)}
    r = client.post(
        "/api/v1/materials/upload",
        files=files,
        data=data,
        headers=_h(admin),
    )
    assert r.status_code in (200, 201), r.text


def test_materials_search_open_to_all_authed(client):
    """Read-endpoint — доступен любому авторизованному."""
    for email in ("kid@example.com", "mom@example.com", "teacher@example.com"):
        tok = _token(client, email)
        r = client.get("/api/v1/materials/search?q=test", headers=_h(tok))
        assert r.status_code == 200, f"{email}: {r.status_code}"


# ============================================================
# PARENT endpoints — только parent
# ============================================================

def test_parent_invite_blocks_student(client):
    kid = _token(client, "kid@example.com")
    r = client.post("/api/v1/parents/invite", headers=_h(kid))
    assert r.status_code == 403


def test_parent_invite_blocks_teacher(client):
    teacher = _token(client, "teacher@example.com")
    r = client.post("/api/v1/parents/invite", headers=_h(teacher))
    assert r.status_code == 403


def test_parent_invite_allows_parent(client):
    mom = _token(client, "mom@example.com")
    r = client.post("/api/v1/parents/invite", headers=_h(mom))
    assert r.status_code == 200


def test_parent_children_blocks_student(client):
    kid = _token(client, "kid@example.com")
    r = client.get("/api/v1/parents/children", headers=_h(kid))
    assert r.status_code == 403


def test_parent_children_allows_parent(client):
    mom = _token(client, "mom@example.com")
    r = client.get("/api/v1/parents/children", headers=_h(mom))
    assert r.status_code == 200


# ============================================================
# STUDENT endpoint — только student
# ============================================================

def test_link_parent_blocks_parent(client):
    mom = _token(client, "mom@example.com")
    r = client.post(
        "/api/v1/students/link-parent",
        json={"code": "INVITE-DUMMY"},
        headers=_h(mom),
    )
    assert r.status_code == 403


def test_link_parent_blocks_teacher(client):
    teacher = _token(client, "teacher@example.com")
    r = client.post(
        "/api/v1/students/link-parent",
        json={"code": "INVITE-DUMMY"},
        headers=_h(teacher),
    )
    assert r.status_code == 403


def test_link_parent_student_wrong_code_returns_400_not_403(client):
    """Ученик с невалидным кодом получает 400 (бизнес-ошибка), а не 403 (RBAC)."""
    kid = _token(client, "kid@example.com")
    r = client.post(
        "/api/v1/students/link-parent",
        json={"code": "INVITE-DUMMY"},
        headers=_h(kid),
    )
    # 400 — ошибка кода, RBAC пропустил
    assert r.status_code == 400


# ============================================================
# Деактивация пользователя
# ============================================================

def test_deactivate_user_blocks_teacher(client):
    teacher = _token(client, "teacher@example.com")
    r = client.post("/api/v1/admin/users/2/deactivate", headers=_h(teacher))
    assert r.status_code == 403
