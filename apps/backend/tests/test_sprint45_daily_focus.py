"""Sprint 4.5+: single-source для parent/dashboard focusToday/helpSignal/weeklyFocus.

Решение владельца (audit 2026-09-05):
- Backend возвращает готовые строки в /api/v1/parents/students/{id}/dashboard
- Поле daily_focus: list[str] — массив из 3 строк (weekly, focusToday, helpSignal)
- Frontend НЕ строит клиентски (раньше было с magic numbers 0.6, [0])

Подход к фикстуре (Sprint 3.43 P1 lesson): создаём свою client_with_parent
локально через copy-paste из test_parent_no_email_leak.py. Это изолирует
Sprint 4.5+ от side effects других тестов (Sprint 4.1 уже использует
эту фикстуру, и cross-file fixture sharing хрупкий в pytest).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.auth.security import hash_password
from app.db.session import Base, SessionLocal, engine, get_db
from app.main import app
from app.subjects.scripts_seed_runner import seed_for_tests
from app.users import models as user_models


@pytest.fixture
def sprint45_client_with_parent():
    """Локальная фикстура для Sprint 4.5+: parent + linked student."""
    # Чистим и пересоздаём schema
    Base.metadata.drop_all(engine)
    engine.dispose()
    Base.metadata.create_all(engine)

    with SessionLocal() as db:
        users = [
            user_models.User(
                email="parent@example.com",
                password_hash=hash_password("strongpass1"),
                display_name="Parent",
                role=user_models.Role.PARENT,
            ),
            user_models.User(
                email="student@example.com",
                password_hash=hash_password("strongpass1"),
                display_name="Linked Student",
                role=user_models.Role.STUDENT,
            ),
        ]
        db.add_all(users)
        db.flush()
        parent, linked_student = users
        seed_for_tests(db, reset=False)
        db.add(
            user_models.ParentStudentLink(
                parent_id=parent.id,
                student_id=linked_student.id,
                status="active",
            )
        )
        db.commit()

    from sqlalchemy import select as _select

    with SessionLocal() as s2:
        linked_id = s2.scalar(
            _select(user_models.User).where(user_models.User.email == "student@example.com")
        ).id

    def _gen():
        s = SessionLocal()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = _gen
    with TestClient(app) as c:
        yield c, linked_id
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


def _login_parent(c: TestClient) -> str:
    r = c.post(
        "/api/v1/auth/login",
        json={"email": "parent@example.com", "password": "strongpass1"},
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_child_dashboard_has_daily_focus_field(sprint45_client_with_parent):
    """Sprint 4.5+: endpoint /students/{id}/dashboard возвращает 'daily_focus'."""
    c, student_id = sprint45_client_with_parent
    token = _login_parent(c)
    headers = {"Authorization": f"Bearer {token}"}
    r = c.get(
        f"/api/v1/parents/students/{student_id}/dashboard",
        headers=headers,
    )
    assert r.status_code == 200, r.text
    body = r.json()

    assert "daily_focus" in body, (
        f"Sprint 4.5+: 'daily_focus' field missing from dashboard. "
        f"Got keys: {list(body.keys())}"
    )
    assert isinstance(body["daily_focus"], list), (
        f"daily_focus must be a list, got {type(body['daily_focus'])}"
    )


def test_daily_focus_max_3_strings(sprint45_client_with_parent):
    """Sprint 4.5+: daily_focus — max 3 строки (weekly, focusToday, helpSignal)."""
    c, student_id = sprint45_client_with_parent
    token = _login_parent(c)
    headers = {"Authorization": f"Bearer {token}"}
    r = c.get(
        f"/api/v1/parents/students/{student_id}/dashboard",
        headers=headers,
    )
    body = r.json()

    assert len(body["daily_focus"]) <= 3, (
        f"Sprint 4.5+: daily_focus max 3, got {len(body['daily_focus'])}"
    )
    for line in body["daily_focus"]:
        assert isinstance(line, str)
        assert len(line) > 0
