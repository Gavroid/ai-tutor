"""Sprint 42: Glucose-aware content difficulty (recovery mode).

T1D safety:
- ❌ НЕ используем AI для medical decisions.
- ❌ НЕ интерпретируем glucose data автоматически.
- ✅ ТОЛЬКО timing-based: если last hypo/hyper session в last 30 мин → recovery_mode=True.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone, timedelta


@pytest.fixture
def client():
    from app.db.session import engine, Base
    from app.main import app

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    return TestClient(app)


@pytest.fixture
def student_login(client):
    """Sprint 42: student register + login."""
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


def test_recommend_next_no_pause_no_recovery(client, student_login):
    """Sprint 42: без session pause → recovery_mode=False."""
    r = client.get(
        "/api/v1/progress/recommend-next",
        headers={"Authorization": f"Bearer {student_login}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["recovery_mode"] is False
    assert data["recovery_reason"] is None
    assert data["minutes_since_pause"] is None


def test_recommend_next_recent_hypo_enables_recovery(client, student_login):
    """Sprint 42: недавняя hypo пауза → recovery_mode=True."""
    from app.db.session import SessionLocal
    from app.sessions.models import SessionPause
    from app.users.models import User
    from jose import jwt
    from app.config import get_settings

    s = get_settings()
    user_id = int(jwt.get_unverified_claims(student_login)["sub"])

    with SessionLocal() as db:
        # Создаём pause 10 мин назад
        recent_pause = SessionPause(
            user_id=user_id,
            topic_id=None,
            reason="hypo",
            started_at=datetime.now(timezone.utc) - timedelta(minutes=10),
        )
        db.add(recent_pause)
        db.commit()

    r = client.get(
        "/api/v1/progress/recommend-next",
        headers={"Authorization": f"Bearer {student_login}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["recovery_mode"] is True
    assert data["recovery_reason"] == "recent_hypo"
    assert data["minutes_since_pause"] is not None
    assert data["minutes_since_pause"] < 30  # within window


def test_recommend_next_recent_hyper_enables_recovery(client, student_login):
    """Sprint 42: недавняя hyper пауза → recovery_mode=True."""
    from app.db.session import SessionLocal
    from app.sessions.models import SessionPause
    from jose import jwt
    from app.config import get_settings

    s = get_settings()
    user_id = int(jwt.get_unverified_claims(student_login)["sub"])

    with SessionLocal() as db:
        recent_pause = SessionPause(
            user_id=user_id,
            topic_id=None,
            reason="hyper",
            started_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        )
        db.add(recent_pause)
        db.commit()

    r = client.get(
        "/api/v1/progress/recommend-next",
        headers={"Authorization": f"Bearer {student_login}"},
    )
    data = r.json()
    assert data["recovery_mode"] is True
    assert data["recovery_reason"] == "recent_hyper"


def test_recommend_next_old_pause_no_recovery(client, student_login):
    """Sprint 42: pause 60 мин назад → recovery_mode=False (за окном)."""
    from app.db.session import SessionLocal
    from app.sessions.models import SessionPause
    from jose import jwt
    from app.config import get_settings

    s = get_settings()
    user_id = int(jwt.get_unverified_claims(student_login)["sub"])

    with SessionLocal() as db:
        old_pause = SessionPause(
            user_id=user_id,
            topic_id=None,
            reason="hypo",
            started_at=datetime.now(timezone.utc) - timedelta(minutes=60),
        )
        db.add(old_pause)
        db.commit()

    r = client.get(
        "/api/v1/progress/recommend-next",
        headers={"Authorization": f"Bearer {student_login}"},
    )
    data = r.json()
    assert data["recovery_mode"] is False
    assert data["minutes_since_pause"] is None or data["minutes_since_pause"] >= 30


def test_recommend_next_break_pause_no_recovery(client, student_login):
    """Sprint 42: 'break' пауза НЕ включает recovery mode (только hypo/hyper)."""
    from app.db.session import SessionLocal
    from app.sessions.models import SessionPause
    from jose import jwt
    from app.config import get_settings

    s = get_settings()
    user_id = int(jwt.get_unverified_claims(student_login)["sub"])

    with SessionLocal() as db:
        break_pause = SessionPause(
            user_id=user_id,
            topic_id=None,
            reason="break",
            started_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        )
        db.add(break_pause)
        db.commit()

    r = client.get(
        "/api/v1/progress/recommend-next",
        headers={"Authorization": f"Bearer {student_login}"},
    )
    data = r.json()
    assert data["recovery_mode"] is False
    assert data["recovery_reason"] is None


def test_recommend_next_response_shape(client, student_login):
    """Sprint 42: response содержит все поля NextTopicOut."""
    r = client.get(
        "/api/v1/progress/recommend-next",
        headers={"Authorization": f"Bearer {student_login}"},
    )
    data = r.json()
    # Все новые поля присутствуют
    assert "recovery_mode" in data
    assert "recovery_reason" in data
    assert "minutes_since_pause" in data
    # Типы
    assert isinstance(data["recovery_mode"], bool)
    assert data["recovery_reason"] is None or isinstance(data["recovery_reason"], str)
    assert data["minutes_since_pause"] is None or isinstance(data["minutes_since_pause"], int)