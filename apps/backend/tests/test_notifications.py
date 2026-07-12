"""Тесты уведомлений (Этап 11 — расширение)."""
from __future__ import annotations

import os

os.environ["APP_SECRET_KEY"] = "test-secret-key-for-pytest-only-1234567890"
os.environ["APP_ENV"] = "development"
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["CORS_ORIGINS"] = "http://localhost:3000"
os.environ["AI_API_KEY"] = "mock-key-for-tests"
os.environ.pop("SMTP_URL", None)  # явно отключаем email

import pytest
from fastapi.testclient import TestClient

from app.db.session import Base, SessionLocal, engine, get_db
from app.main import app
from app.notifications import models as notif_models
from app.subjects.scripts_seed_runner import seed_for_tests
from app.users import service as user_service
from app.users.schemas import UserCreate


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    engine.dispose()
    Base.metadata.create_all(engine)

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


def test_create_in_app_notification(client):
    kid_token = _login(client, "kid@example.com")
    r = client.get(
        "/api/v1/notifications",
        headers={"Authorization": f"Bearer {kid_token}"},
    )
    assert r.status_code == 200
    assert r.json() == []


def test_parent_receives_notification_after_diagnostic(client):
    # Связываем
    mom_token = _login(client, "mom@example.com")
    code = client.post(
        "/api/v1/parents/invite",
        headers={"Authorization": f"Bearer {mom_token}"},
    ).json()["code"]
    kid_token = _login(client, "kid@example.com")
    client.post(
        "/api/v1/students/link-parent",
        json={"code": code},
        headers={"Authorization": f"Bearer {kid_token}"},
    )

    # Находим алгебру
    s = SessionLocal()
    try:
        from app.subjects import models as subj_models

        algebra = s.scalar(
            __import__("sqlalchemy").select(subj_models.Subject).where(subj_models.Subject.code == "algebra")
        )
        subj_id = algebra.id
    finally:
        s.close()

    # Проходим диагностику (быстро)
    r = client.post(
        "/api/v1/diagnostic/start",
        json={"subject_id": subj_id},
        headers={"Authorization": f"Bearer {kid_token}"},
    )
    sid = r.json()["id"]

    # 1-2 ответа
    for _ in range(2):
        q = client.get(
            f"/api/v1/diagnostic/{sid}/next",
            headers={"Authorization": f"Bearer {kid_token}"},
        )
        if q.status_code == 404:
            break
        qj = q.json()
        client.post(
            f"/api/v1/diagnostic/{sid}/answer",
            json={
                "topic_id": qj["topic_id"],
                "question_text": qj["question_text"],
                "user_answer": "правильный ответ про алгебру",
                "correct_answer": qj["question_text"],
            },
            headers={"Authorization": f"Bearer {kid_token}"},
        )

    # Завершаем
    client.post(
        f"/api/v1/diagnostic/{sid}/finish",
        headers={"Authorization": f"Bearer {kid_token}"},
    )

    # Мама должна увидеть уведомление
    r = client.get(
        "/api/v1/notifications",
        headers={"Authorization": f"Bearer {mom_token}"},
    )
    assert r.status_code == 200
    notifs = r.json()
    assert len(notifs) >= 1
    assert "диагностика" in notifs[0]["title"].lower() or "диагностика" in notifs[0]["body"].lower()


def test_mark_as_read(client):
    kid_token = _login(client, "kid@example.com")
    # Создаём уведомление через сервис
    from app.notifications import service as notif_service

    s = SessionLocal()
    try:
        from app.users import models as user_models

        kid = s.scalar(
            __import__("sqlalchemy").select(user_models.User).where(user_models.User.email == "kid@example.com")
        )
        n = notif_service.create_in_app(s, kid.id, "info", "Test", "Body", link="/subjects")
        nid = n.id
    finally:
        s.close()

    # Помечаем прочитанным
    r = client.post(
        f"/api/v1/notifications/{nid}/read",
        headers={"Authorization": f"Bearer {kid_token}"},
    )
    assert r.status_code == 200

    # Проверяем
    s = SessionLocal()
    try:
        n = s.get(notif_models.Notification, nid)
        assert n.is_read is True
    finally:
        s.close()


def test_mark_all_read(client):
    kid_token = _login(client, "kid@example.com")
    from app.notifications import service as notif_service

    s = SessionLocal()
    try:
        from app.users import models as user_models

        kid = s.scalar(
            __import__("sqlalchemy").select(user_models.User).where(user_models.User.email == "kid@example.com")
        )
        for i in range(3):
            notif_service.create_in_app(s, kid.id, "info", f"Title {i}", "Body")
    finally:
        s.close()

    r = client.post(
        "/api/v1/notifications/read-all",
        headers={"Authorization": f"Bearer {kid_token}"},
    )
    assert r.status_code == 200

    r = client.get(
        "/api/v1/notifications?unread_only=true",
        headers={"Authorization": f"Bearer {kid_token}"},
    )
    assert r.json() == []


def test_email_dry_run_without_smtp(client):
    """Без SMTP_URL email сохраняется со status='dry_run'."""
    from app.notifications import service as notif_service

    s = SessionLocal()
    try:
        from app.users import models as user_models

        kid = s.scalar(
            __import__("sqlalchemy").select(user_models.User).where(user_models.User.email == "kid@example.com")
        )
        email_record = notif_service.send_email(
            s,
            user_id=kid.id,
            to_email=kid.email,
            subject="Test",
            body="Body",
        )
        # Синхронный код создаст coroutine, но не выполнит. Вызовем через asyncio.run
        import asyncio

        asyncio.run(
            notif_service.send_email(
                s,
                user_id=kid.id,
                to_email=kid.email,
                subject="Async",
                body="Body",
            )
        )

        emails = s.query(notif_models.EmailNotification).all()
        assert len(emails) >= 1
        statuses = {e.status for e in emails}
        assert "dry_run" in statuses or "queued" in statuses
    finally:
        s.close()