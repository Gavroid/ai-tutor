"""Sprint 34: тесты для session pause (T1D safety)."""
from __future__ import annotations

import os

# Sprint 34 fix: in-memory SQLite с shared cache, чтобы разные соединения
# видели одни и те же таблицы. Без cache=shared каждый connect() создаёт
# отдельную БД.
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///file:memdb1?mode=memory&cache=shared&uri=true"

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from app.db.session import engine, Base
    from app.main import app

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    return TestClient(app)


@pytest.fixture
def student_login(client):
    """Регистрирует student и логинит → token."""
    r = client.post(
        "/api/v1/auth/register",
        json={
            "email": "kirill@example.com",
            "password": "Kirill2026!",
            "display_name": "Кирилл",
            "role": "student",
            "grade": 7,
        },
    )
    assert r.status_code == 201, r.text
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "kirill@example.com", "password": "Kirill2026!"},
    )
    return r.json()["access_token"]


def test_create_pause_returns_id_and_reason(client, student_login):
    """Sprint 34: POST /sessions/pause создаёт pause."""
    r = client.post(
        "/api/v1/sessions/pause",
        json={"reason": "break", "topic_id": None},
        headers={"Authorization": f"Bearer {student_login}"},
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert "id" in data
    assert data["reason"] == "break"
    assert "started_at" in data


def test_create_pause_with_topic_id(client, student_login):
    """Sprint 34: pause связан с topic_id."""
    r = client.post(
        "/api/v1/sessions/pause",
        json={"reason": "hypo", "topic_id": 1},
        headers={"Authorization": f"Bearer {student_login}"},
    )
    assert r.status_code == 201


def test_create_pause_invalid_reason_returns_422(client, student_login):
    """Sprint 34: invalid reason → 422 (Pydantic validation)."""
    r = client.post(
        "/api/v1/sessions/pause",
        json={"reason": "lunch"},  # Не break/hypo/hyper/other
        headers={"Authorization": f"Bearer {student_login}"},
    )
    assert r.status_code == 422


def test_create_pause_unauthenticated_returns_401(client):
    """Sprint 34: без auth → 401."""
    r = client.post("/api/v1/sessions/pause", json={"reason": "break"})
    assert r.status_code == 401


def test_resume_pause_returns_seconds(client, student_login):
    """Sprint 34: resume возвращает paused_seconds."""
    # Create
    client.post(
        "/api/v1/sessions/pause",
        json={"reason": "hypo"},
        headers={"Authorization": f"Bearer {student_login}"},
    )

    # Resume
    r = client.post(
        "/api/v1/sessions/resume",
        headers={"Authorization": f"Bearer {student_login}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert "paused_seconds" in data
    assert data["paused_seconds"] >= 0
    assert data["reason"] == "hypo"


def test_resume_without_pause_returns_404(client, student_login):
    """Sprint 34: resume без активной pause → 404."""
    r = client.post(
        "/api/v1/sessions/resume",
        headers={"Authorization": f"Bearer {student_login}"},
    )
    assert r.status_code == 404


def test_list_recent_pauses(client, student_login):
    """Sprint 34: GET /sessions/pauses/recent возвращает список."""
    # Create 3 pauses с явными started_at через прямой INSERT
    # (in-memory SQLite: server_default NOW() одинаковый для всех записей в 1 транзакции).
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import text
    from app.db.session import engine as eng
    from app.common.deps import get_current_user

    base = datetime.now(timezone.utc)
    headers = {"Authorization": f"Bearer {student_login}"}

    with eng.begin() as conn:
        # Получаем user_id из текущего токена (JWT subject).
        from jose import jwt
        from app.config import get_settings
        s = get_settings()
        token = headers["Authorization"].split()[1]
        user_id = int(jwt.get_unverified_claims(token)["sub"])

        # 3 pause с разными started_at (по секунде назад).
        for i, reason in enumerate(["break", "hypo", "other"]):
            started = base - timedelta(seconds=10 - i)
            conn.execute(
                text(
                    "INSERT INTO session_pauses (user_id, topic_id, reason, started_at) "
                    "VALUES (:uid, NULL, :r, :ts)"
                ),
                {"uid": user_id, "r": reason, "ts": started},
            )

    r = client.get(
        "/api/v1/sessions/pauses/recent",
        headers=headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 3
    # Новые первыми (ORDER BY started_at DESC): "other" последний вставлен
    assert data[0]["reason"] == "other"
    assert data[1]["reason"] == "hypo"
    assert data[2]["reason"] == "break"


def test_list_recent_pauses_limit_validation(client, student_login):
    """Sprint 34: limit > 100 или < 1 → 400."""
    r = client.get(
        "/api/v1/sessions/pauses/recent?limit=200",
        headers={"Authorization": f"Bearer {student_login}"},
    )
    assert r.status_code == 400


def test_pause_does_not_affect_streak(client, student_login):
    """Sprint 34: pause НЕ ломает streak (T1D-friendly).

    Sprint 34 NOTE: логика streak должна быть separate от pause.
    Pause — только для analytics и parent dashboard.
    """
    # Pause
    r1 = client.post(
        "/api/v1/sessions/pause",
        json={"reason": "hypo"},
        headers={"Authorization": f"Bearer {student_login}"},
    )
    assert r1.status_code == 201

    # Streak endpoint всё ещё работает
    r2 = client.get(
        "/api/v1/student/streak",
        headers={"Authorization": f"Bearer {student_login}"},
    )
    assert r2.status_code == 200
    # Streak не сломан (current может быть 0, но не отрицательный)
    assert r2.json()["current_streak_days"] >= 0