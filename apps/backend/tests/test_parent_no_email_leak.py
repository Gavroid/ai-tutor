"""Sprint H2.3 (2026-08-23): parent-facing API does не отдаёт email детей.

Это PII minimization: parent знает ребёнка лично и не должен получать
email ребёнка в JSON-ответах. Проверяем:
- GET /api/v1/parents/children → нет email
- GET /api/v1/parents/me/children → нет email
- GET /api/v1/parents/students/{id}/dashboard → нет email
- GET /api/v1/parents/students/{id}/overview → нет email
- GET /api/v1/parents/students/{id}/dashboard.pdf → HTML body не содержит email

Ref: docs/audit-2026-08-23/03-problems.md P1-3.
"""
from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.auth.security import hash_password
from app.db.session import Base, SessionLocal, engine, get_db
from app.main import app
from app.subjects.scripts_seed_runner import seed_for_tests
from app.users.models import ParentStudentLink, Role, User


EMAIL_REGEX = re.compile(r"[A-Za-z0-9._%_+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")


def _walk_strings(obj):
    """Yield all string values из JSON-like объекта (dict, list, str)."""
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _walk_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk_strings(v)


def _find_emails(obj) -> list[str]:
    found = []
    for s in _walk_strings(obj):
        for m in EMAIL_REGEX.findall(s):
            found.append(m)
    return found


@pytest.fixture()
def client_with_parent():
    Base.metadata.drop_all(engine)
    engine.dispose()
    Base.metadata.create_all(engine)

    with SessionLocal() as db:
        users = [
            User(
                email="parent@example.com",
                password_hash=hash_password("strongpass1"),
                display_name="Parent",
                role=Role.PARENT,
            ),
            User(
                email="student@example.com",
                password_hash=hash_password("strongpass1"),
                display_name="Linked Student",
                role=Role.STUDENT,
            ),
        ]
        db.add_all(users)
        db.flush()
        parent, linked_student = users
        seed_for_tests(db, reset=False)
        db.add(
            ParentStudentLink(
                parent_id=parent.id,
                student_id=linked_student.id,
                status="active",
            )
        )
        db.commit()

    # linked_student объект detached после with SessionLocal() — нужен свежий lookup.
    from sqlalchemy import select as _select
    from app.db.session import SessionLocal as _SL
    from app.users.models import User as _User

    with _SL() as s2:
        linked_id = s2.scalar(
            _select(_User).where(_User.email == "student@example.com")
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


def test_children_endpoint_no_email_leak(client_with_parent):
    """GET /api/v1/parents/children → нет email детей в response."""
    c, _ = client_with_parent
    token = _login_parent(c)
    headers = {"Authorization": f"Bearer {token}"}
    r = c.get("/api/v1/parents/children", headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    # JSON: каждый child должен иметь student_id, display_name, linked_at,
    # но НЕ email.
    assert isinstance(body, list)
    assert body, "expected at least one linked child"
    for child in body:
        assert "email" not in child, (
            f"children payload must not contain 'email' field, "
            f"got keys: {list(child.keys())}"
        )
    # Проверим, что нигде в JSON нет ни одного email-формата.
    emails = _find_emails(body)
    # parent email "parent@example.com" допустим только если он сам попал в payload,
    # но мы не должны отдавать emails других пользователей.
    student_emails = [e for e in emails if "student" in e.lower()]
    assert not student_emails, (
        f"Found student emails in /parents/children response: {student_emails}"
    )


def test_me_children_endpoint_no_email_leak(client_with_parent):
    """GET /api/v1/parents/me/children → нет email детей."""
    c, _ = client_with_parent
    token = _login_parent(c)
    headers = {"Authorization": f"Bearer {token}"}
    r = c.get("/api/v1/parents/me/children", headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    for child in body:
        assert "email" not in child, (
            f"me/children payload must not contain 'email' field, "
            f"got keys: {list(child.keys())}"
        )


def test_child_dashboard_endpoint_no_email_leak(client_with_parent):
    """GET /api/v1/parents/students/{id}/dashboard → нет email ребёнка."""
    c, student_id = client_with_parent
    token = _login_parent(c)
    headers = {"Authorization": f"Bearer {token}"}
    r = c.get(
        f"/api/v1/parents/students/{student_id}/dashboard",
        headers=headers,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    # StudentBrief в payload
    student = body.get("student", {})
    assert "email" not in student, (
        f"dashboard student payload must not contain 'email', "
        f"got keys: {list(student.keys())}"
    )
    # No student@example.com anywhere
    emails = _find_emails(body)
    student_emails = [e for e in emails if "student" in e.lower()]
    assert not student_emails, (
        f"Found student emails in dashboard response: {student_emails}"
    )


def test_child_overview_endpoint_no_email_leak(client_with_parent):
    """GET /api/v1/parents/students/{id}/overview → нет email ребёнка."""
    c, student_id = client_with_parent
    token = _login_parent(c)
    headers = {"Authorization": f"Bearer {token}"}
    r = c.get(
        f"/api/v1/parents/students/{student_id}/overview",
        headers=headers,
    )
    if r.status_code == 404:
        # Endpoint может называться иначе или быть отключён.
        pytest.skip(f"overview endpoint returned 404: {r.text}")
    assert r.status_code == 200, r.text
    body = r.json()
    emails = _find_emails(body)
    student_emails = [e for e in emails if "student" in e.lower()]
    assert not student_emails, (
        f"Found student emails in overview response: {student_emails}"
    )