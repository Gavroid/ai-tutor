"""Sprint 59: multi-child support tests.

Покрывает:
- /me/children alias
- /me/children/count endpoint
- multi-child linking (parent → multiple students)
"""
from __future__ import annotations

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
def parent_with_2_children(client):
    """Sprint 59: parent + 2 students (multi-child)."""
    from sqlalchemy.orm import Session
    from app.db.session import engine
    from app.users.models import User, Role, ParentStudentLink
    from app.auth.security import hash_password

    with Session(engine) as db:
        # Create parent
        parent = User(
            email="parent@example.com",
            password_hash=hash_password("Kirill2026!"),
            display_name="Parent",
            role=Role.PARENT,
            is_active=True,
        )
        db.add(parent)
        db.commit()
        db.refresh(parent)

        # Create 2 students
        students = []
        for i in range(2):
            s = User(
                email=f"child{i}@example.com",
                password_hash=hash_password("Kirill2026!"),
                display_name=f"Child {i}",
                role=Role.STUDENT,
                is_active=True,
            )
            db.add(s)
            students.append(s)
        db.commit()
        for s in students:
            db.refresh(s)

        # Link parent → both students
        for s in students:
            link = ParentStudentLink(
                parent_id=parent.id,
                student_id=s.id,
                status="active",
            )
            db.add(link)
        db.commit()

        return parent, [s.id for s in students]


def test_parent_with_no_children(client):
    """Sprint 59: parent без детей → пустой list."""
    from sqlalchemy.orm import Session
    from app.db.session import engine
    from app.users.models import User, Role
    from app.auth.security import hash_password

    with Session(engine) as db:
        parent = User(
            email="lonely@example.com",
            password_hash=hash_password("Kirill2026!"),
            display_name="Lonely",
            role=Role.PARENT,
            is_active=True,
        )
        db.add(parent)
        db.commit()

    r = client.post(
        "/api/v1/auth/login",
        json={"email": "lonely@example.com", "password": "Kirill2026!"},
    )
    token = r.json()["access_token"]

    r2 = client.get(
        "/api/v1/parents/children",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 200
    assert r2.json() == []


def test_parent_with_one_child(client):
    """Sprint 59: parent с 1 child → list из 1."""
    from sqlalchemy.orm import Session
    from app.db.session import engine
    from app.users.models import User, Role, ParentStudentLink
    from app.auth.security import hash_password

    with Session(engine) as db:
        parent = User(
            email="p1@example.com",
            password_hash=hash_password("Kirill2026!"),
            display_name="P1",
            role=Role.PARENT,
            is_active=True,
        )
        db.add(parent)
        db.commit()
        child = User(
            email="c1@example.com",
            password_hash=hash_password("Kirill2026!"),
            display_name="C1",
            role=Role.STUDENT,
            is_active=True,
        )
        db.add(child)
        db.commit()
        link = ParentStudentLink(parent_id=parent.id, student_id=child.id, status="active")
        db.add(link)
        db.commit()

    r = client.post(
        "/api/v1/auth/login",
        json={"email": "p1@example.com", "password": "Kirill2026!"},
    )
    token = r.json()["access_token"]

    r2 = client.get(
        "/api/v1/parents/children",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 200
    children = r2.json()
    assert len(children) == 1
    assert children[0]["display_name"] == "C1"
    assert children[0]["email"] == "c1@example.com"


def test_parent_with_two_children(client, parent_with_2_children):
    """Sprint 59: parent с 2 children → list из 2."""
    parent, child_ids = parent_with_2_children

    r = client.post(
        "/api/v1/auth/login",
        json={"email": "parent@example.com", "password": "Kirill2026!"},
    )
    token = r.json()["access_token"]

    r2 = client.get(
        "/api/v1/parents/children",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 200
    children = r2.json()
    assert len(children) == 2
    student_ids = [c["student_id"] for c in children]
    assert set(student_ids) == set(child_ids)


def test_me_children_alias(client, parent_with_2_children):
    """Sprint 59: /me/children = /children (alias)."""
    parent, child_ids = parent_with_2_children

    r = client.post(
        "/api/v1/auth/login",
        json={"email": "parent@example.com", "password": "Kirill2026!"},
    )
    token = r.json()["access_token"]

    r1 = client.get(
        "/api/v1/parents/children",
        headers={"Authorization": f"Bearer {token}"},
    )
    r2 = client.get(
        "/api/v1/parents/me/children",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json() == r2.json()


def test_me_children_count(client, parent_with_2_children):
    """Sprint 59: /me/children/count → 2."""
    parent, child_ids = parent_with_2_children

    r = client.post(
        "/api/v1/auth/login",
        json={"email": "parent@example.com", "password": "Kirill2026!"},
    )
    token = r.json()["access_token"]

    r2 = client.get(
        "/api/v1/parents/me/children/count",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 200
    data = r2.json()
    assert data["count"] == 2
    assert "parent_id" in data


def test_me_children_count_no_children(client):
    """Sprint 59: parent без детей → count=0."""
    from sqlalchemy.orm import Session
    from app.db.session import engine
    from app.users.models import User, Role
    from app.auth.security import hash_password

    with Session(engine) as db:
        parent = User(
            email="empty@example.com",
            password_hash=hash_password("Kirill2026!"),
            display_name="Empty",
            role=Role.PARENT,
            is_active=True,
        )
        db.add(parent)
        db.commit()

    r = client.post(
        "/api/v1/auth/login",
        json={"email": "empty@example.com", "password": "Kirill2026!"},
    )
    token = r.json()["access_token"]

    r2 = client.get(
        "/api/v1/parents/me/children/count",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 200
    assert r2.json()["count"] == 0


def test_me_children_requires_parent(client):
    """Sprint 59: student role → 403."""
    from sqlalchemy.orm import Session
    from app.db.session import engine
    from app.users.models import User, Role
    from app.auth.security import hash_password

    with Session(engine) as db:
        student = User(
            email="s@example.com",
            password_hash=hash_password("Kirill2026!"),
            display_name="Student",
            role=Role.STUDENT,
            is_active=True,
        )
        db.add(student)
        db.commit()

    r = client.post(
        "/api/v1/auth/login",
        json={"email": "s@example.com", "password": "Kirill2026!"},
    )
    assert r.status_code == 200
    token = r.json()["access_token"]

    r2 = client.get(
        "/api/v1/parents/me/children",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 403


def test_unlinked_child_not_in_list(client):
    """Sprint 59: unlinked child НЕ в списке parent."""
    from sqlalchemy.orm import Session
    from app.db.session import engine
    from app.users.models import User, Role
    from app.auth.security import hash_password

    with Session(engine) as db:
        parent = User(
            email="p2@example.com",
            password_hash=hash_password("Kirill2026!"),
            display_name="P2",
            role=Role.PARENT,
            is_active=True,
        )
        db.add(parent)
        db.commit()
        # Create unlinked child
        child = User(
            email="unlinked@example.com",
            password_hash=hash_password("Kirill2026!"),
            display_name="Unlinked",
            role=Role.STUDENT,
            is_active=True,
        )
        db.add(child)
        db.commit()

    r = client.post(
        "/api/v1/auth/login",
        json={"email": "p2@example.com", "password": "Kirill2026!"},
    )
    token = r.json()["access_token"]

    r2 = client.get(
        "/api/v1/parents/children",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 200
    children = r2.json()
    assert len(children) == 0  # unlinked not in list


def test_me_children_unauthorized(client):
    """Sprint 59: /me/children без auth → 401."""
    r = client.get("/api/v1/parents/me/children")
    assert r.status_code == 401