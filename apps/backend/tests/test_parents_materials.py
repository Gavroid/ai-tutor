"""Тесты родительского кабинета и материалов (Этапы 9, 10)."""
from __future__ import annotations

import os

os.environ["APP_SECRET_KEY"] = "test-secret-key-for-pytest-only-1234567890"
os.environ["APP_ENV"] = "development"
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["CORS_ORIGINS"] = "http://localhost:3000"
os.environ["AI_API_KEY"] = "mock-key-for-tests"
os.environ["UPLOAD_DIR"] = "/tmp/ai-tutor-test-uploads"

import io
import pytest
from fastapi.testclient import TestClient

from app.db.session import Base, SessionLocal, engine, get_db
from app.main import app
from app.subjects import models as subj_models
from app.subjects.scripts_seed_runner import seed_for_tests
from app.users import service as user_service
from app.users.schemas import UserCreate


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    engine.dispose()
    Base.metadata.create_all(engine)

    # parent + student
    s = SessionLocal()
    try:
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
        # teacher для загрузки материалов
        user_service.register_user(
            s,
            UserCreate(
                email="teacher@example.com",
                password="strongpass1",
                display_name="Учитель",
                role="teacher",
            ),
            allow_private_bypass=True,
        )
        seed_for_tests(s, reset=False)
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
        yield c
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


def _login(c: TestClient, email: str) -> str:
    return c.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "strongpass1"},
    ).json()["access_token"]


def _first_algebra_topic_id() -> int:
    s = SessionLocal()
    try:
        algebra = s.scalar(
            __import__("sqlalchemy").select(subj_models.Subject).where(subj_models.Subject.code == "algebra")
        )
        topic = s.scalar(
            __import__("sqlalchemy").select(subj_models.Topic)
            .join(subj_models.Section)
            .where(subj_models.Section.subject_id == algebra.id)
            .limit(1)
        )
        return topic.id
    finally:
        s.close()


# ===== Parents =====


def test_parent_create_invite(client):
    token = _login(client, "mom@example.com")
    r = client.post(
        "/api/v1/parents/invite",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    code = r.json()["code"]
    assert code.startswith("P-")
    assert len(code) >= 10


def test_parent_invite_requires_parent_role(client):
    token = _login(client, "kid@example.com")
    r = client.post(
        "/api/v1/parents/invite",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403


def test_full_parent_linking_flow(client):
    # 1. Parent creates invite
    mom_token = _login(client, "mom@example.com")
    code = client.post(
        "/api/v1/parents/invite",
        headers={"Authorization": f"Bearer {mom_token}"},
    ).json()["code"]

    # 2. Kid accepts
    kid_token = _login(client, "kid@example.com")
    r = client.post(
        "/api/v1/students/link-parent",
        json={"code": code},
        headers={"Authorization": f"Bearer {kid_token}"},
    )
    assert r.status_code == 200
    assert r.json()["ok"] is True

    # 3. Kid records some progress
    tid = _first_algebra_topic_id()
    for is_correct in [True, False, True]:
        client.post(
            "/api/v1/progress/attempts",
            headers={"Authorization": f"Bearer {kid_token}"},
            json={
                "topic_id": tid,
                "question_text": "q",
                "user_answer": "a",
                "correct_answer": "a" if is_correct else "b",
                "is_correct": is_correct,
                "score": 1.0 if is_correct else 0.0,
                "feedback": "ok" if is_correct else "Неверно",
            },
        )

    # 4. Parent sees children list
    r = client.get(
        "/api/v1/parents/children",
        headers={"Authorization": f"Bearer {mom_token}"},
    )
    assert r.status_code == 200
    children = r.json()
    assert len(children) == 1
    assert children[0]["display_name"] == "Кирилл"

    # 5. Parent sees overview
    kid_id = children[0]["student_id"]
    r = client.get(
        f"/api/v1/parents/children/{kid_id}",
        headers={"Authorization": f"Bearer {mom_token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["student"]["display_name"] == "Кирилл"
    assert body["total_attempts"] == 3
    assert body["correct_attempts"] == 2
    assert 0.6 < body["accuracy"] < 0.7
    assert "privacy_note" in body


def test_parent_cannot_view_unlinked_child(client):
    mom_token = _login(client, "mom@example.com")
    # No invite accepted → no linked children
    r = client.get(
        "/api/v1/parents/children/99999",
        headers={"Authorization": f"Bearer {mom_token}"},
    )
    assert r.status_code == 404


def test_link_with_invalid_code(client):
    kid_token = _login(client, "kid@example.com")
    r = client.post(
        "/api/v1/students/link-parent",
        json={"code": "INVALID-CODE"},
        headers={"Authorization": f"Bearer {kid_token}"},
    )
    assert r.status_code == 400


# ===== Materials =====


def test_upload_material_txt(client):
    teacher_token = _login(client, "teacher@example.com")
    tid = _first_algebra_topic_id()
    content = "# Степени с натуральным показателем\n\nСтепень числа a в степени n — это произведение n множителей, каждый из которых равен a.".encode("utf-8")
    r = client.post(
        "/api/v1/materials/upload",
        headers={"Authorization": f"Bearer {teacher_token}"},
        data={"topic_id": tid, "source": "Учебник 2024"},
        files={"file": ("lesson.txt", io.BytesIO(content), "text/plain")},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["topic_id"] == tid
    assert body["title"] == "lesson.txt"
    # Загружено успешно — файл сохранён в UPLOAD_DIR
    import os
    files = os.listdir(os.environ["UPLOAD_DIR"])
    assert any("lesson.txt" in f for f in files)


def test_upload_requires_teacher_role(client):
    kid_token = _login(client, "kid@example.com")
    tid = _first_algebra_topic_id()
    r = client.post(
        "/api/v1/materials/upload",
        headers={"Authorization": f"Bearer {kid_token}"},
        data={"topic_id": tid},
        files={"file": ("lesson.txt", io.BytesIO(b"text"), "text/plain")},
    )
    assert r.status_code == 403


def test_search_materials(client):
    teacher_token = _login(client, "teacher@example.com")
    kid_token = _login(client, "kid@example.com")
    tid = _first_algebra_topic_id()
    content = "Уникальное слово зеленоперсиковый для поиска в материалах. Просто текст.".encode("utf-8")
    client.post(
        "/api/v1/materials/upload",
        headers={"Authorization": f"Bearer {teacher_token}"},
        data={"topic_id": tid},
        files={"file": ("special.txt", io.BytesIO(content), "text/plain")},
    )
    r = client.get(
        "/api/v1/materials/search?q=зеленоперсиковый",
        headers={"Authorization": f"Bearer {kid_token}"},
    )
    assert r.status_code == 200
    hits = r.json()
    assert len(hits) >= 1
    assert "зеленоперсиковый" in hits[0]["snippet"]


def test_upload_rejects_bad_extension(client):
    teacher_token = _login(client, "teacher@example.com")
    tid = _first_algebra_topic_id()
    r = client.post(
        "/api/v1/materials/upload",
        headers={"Authorization": f"Bearer {teacher_token}"},
        data={"topic_id": tid},
        files={"file": ("malware.exe", io.BytesIO(b"data"), "application/octet-stream")},
    )
    assert r.status_code == 400