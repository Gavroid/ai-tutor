"""Sprint 35: тесты для teacher search + bulk approve."""
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
def teacher_login(client):
    """Sоздаёт teacher через прямой SQL (НЕ через /auth/register — 403 для teacher).

    Sprint 35: teacher регистрируется только через seed_users CLI
    с PILOT_SEED_TOKEN. В тесте создаём напрямую через ORM.
    """
    from sqlalchemy.orm import Session
    from app.db.session import engine
    from app.users.models import User, Role
    from app.auth.security import hash_password

    with Session(engine) as db:
        user = User(
            email="teacher@example.com",
            password_hash=hash_password("Kirill2026!"),
            display_name="Учитель",
            role=Role.TEACHER,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    r = client.post(
        "/api/v1/auth/login",
        json={"email": "teacher@example.com", "password": "Kirill2026!"},
    )
    return r.json()["access_token"]


    def test_list_materials_with_search(client, teacher_login):
        """Sprint 35: GET /teacher/materials?search=... фильтрует по title."""
        # Создаём 3 материала с ASCII titles (для совместимости с SQLite LIKE).
        from app.db.session import SessionLocal
        from app.subjects.models import LearningMaterial
        from jose import jwt
        from app.config import get_settings

        s = get_settings()
        token = teacher_login
        user_id = int(jwt.get_unverified_claims(token)["sub"])

        with SessionLocal() as db:
            from app.subjects.models import Subject, Section, Topic
            subject = Subject(code="math", name="Math")
            db.add(subject)
            db.flush()
            section = Section(subject_id=subject.id, name="Algebra")
            db.add(section)
            db.flush()
            topic = Topic(section_id=section.id, name="Test topic", order_index=1)
            db.add(topic)
            db.flush()

            for title in ["Algebra intro", "Geometry basic", "Algebra advanced"]:
                mat = LearningMaterial(
                    generated_by=user_id,
                    topic_id=topic.id,
                    title=title,
                    content="# content",
                    status="ai_generated",
                )
                db.add(mat)
            db.commit()

        # Без search — 3
        r = client.get(
            "/api/v1/teacher/materials",
            headers={"Authorization": f"Bearer {teacher_login}"},
        )
        assert r.status_code == 200
        assert len(r.json()) == 3

        # search=algebra (case-insensitive) — 2
        r = client.get(
            "/api/v1/teacher/materials?search=algebra",
            headers={"Authorization": f"Bearer {teacher_login}"},
        )
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 2
        titles = [m["title"] for m in data]
        assert "Algebra intro" in titles
        assert "Algebra advanced" in titles
        assert "Geometry basic" not in titles

        # search=geometry — 1
        r = client.get(
            "/api/v1/teacher/materials?search=geometry",
            headers={"Authorization": f"Bearer {teacher_login}"},
        )
        assert r.status_code == 200
        assert len(r.json()) == 1


def test_list_materials_search_combined_with_filters(client, teacher_login):
    """Sprint 35: search + status + topic_id работают вместе."""
    from app.db.session import SessionLocal
    from app.subjects.models import LearningMaterial, Subject, Section, Topic
    from jose import jwt
    from app.config import get_settings

    s = get_settings()
    token = teacher_login
    user_id = int(jwt.get_unverified_claims(token)["sub"])

    with SessionLocal() as db:
        subject = Subject(code="M", name="M")
        db.add(subject)
        db.flush()
        section = Section(subject_id=subject.id, name="Alg")
        db.add(section)
        db.flush()
        topic = Topic(section_id=section.id, name="T", order_index=1)
        db.add(topic)
        db.flush()

        # 2 с "Algebra" (ai_generated), 1 без (published)
        for title, status in [
            ("Algebra 1", "ai_generated"),
            ("Algebra 2", "ai_generated"),
            ("Geometry", "published"),
        ]:
            mat = LearningMaterial(
                generated_by=user_id,
                topic_id=topic.id,
                title=title,
                content="# c",
                status=status,
            )
            db.add(mat)
        db.commit()

    # search + status=ai_generated — должно найти 2
    r = client.get(
        "/api/v1/teacher/materials?search=algebra&status=ai_generated",
        headers={"Authorization": f"Bearer {teacher_login}"},
    )
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_list_materials_search_empty(client, teacher_login):
    """Sprint 35: search без совпадений → пустой список."""
    r = client.get(
        "/api/v1/teacher/materials?search=nonexistent",
        headers={"Authorization": f"Bearer {teacher_login}"},
    )
    assert r.status_code == 200
    assert r.json() == []


def test_bulk_approve_all_success(client, teacher_login):
    """Sprint 35: bulk approve нескольких материалов сразу."""
    from app.db.session import SessionLocal
    from app.subjects.models import LearningMaterial, Subject, Section, Topic
    from jose import jwt
    from app.config import get_settings

    s = get_settings()
    user_id = int(jwt.get_unverified_claims(teacher_login)["sub"])

    with SessionLocal() as db:
        subject = Subject(code="M", name="M")
        db.add(subject); db.flush()
        section = Section(subject_id=subject.id, name="S")
        db.add(section); db.flush()
        topic = Topic(section_id=section.id, name="T", order_index=1)
        db.add(topic); db.flush()

        material_ids = []
        for i in range(3):
            mat = LearningMaterial(
                generated_by=user_id,
                topic_id=topic.id,
                title=f"Mat {i}",
                content="# c",
                status="ai_generated",
            )
            db.add(mat); db.flush()
            material_ids.append(mat.id)
        db.commit()

    r = client.post(
        "/api/v1/teacher/materials/bulk-approve",
        json={"material_ids": material_ids},
        headers={"Authorization": f"Bearer {teacher_login}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert len(data["approved"]) == 3
    assert data["failed"] == []
    assert set(data["approved"]) == set(material_ids)


def test_bulk_approve_partial_failure(client, teacher_login):
    """Sprint 35: bulk approve с частичным failure — failed + approved раздельно."""
    from app.db.session import SessionLocal
    from app.subjects.models import LearningMaterial, Subject, Section, Topic
    from jose import jwt
    from app.config import get_settings

    s = get_settings()
    user_id = int(jwt.get_unverified_claims(teacher_login)["sub"])

    with SessionLocal() as db:
        subject = Subject(code="M", name="M")
        db.add(subject); db.flush()
        section = Section(subject_id=subject.id, name="S")
        db.add(section); db.flush()
        topic = Topic(section_id=section.id, name="T", order_index=1)
        db.add(topic); db.flush()

        # 2 valid + 1 nonexistent ID
        valid_ids = []
        for i in range(2):
            mat = LearningMaterial(
                generated_by=user_id,
                topic_id=topic.id,
                title=f"Valid {i}",
                content="# c",
                status="ai_generated",
            )
            db.add(mat); db.flush()
            valid_ids.append(mat.id)
        db.commit()

    r = client.post(
        "/api/v1/teacher/materials/bulk-approve",
        json={"material_ids": valid_ids + [99999]},
        headers={"Authorization": f"Bearer {teacher_login}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data["approved"]) == 2
    assert len(data["failed"]) == 1
    assert data["failed"][0]["id"] == "99999"
    assert data["failed"][0]["reason"] == "not_found"


def test_bulk_approve_empty_list_422(client, teacher_login):
    """Sprint 35: пустой material_ids → 422 (Pydantic)."""
    r = client.post(
        "/api/v1/teacher/materials/bulk-approve",
        json={"material_ids": []},
        headers={"Authorization": f"Bearer {teacher_login}"},
    )
    assert r.status_code == 422


def test_bulk_approve_too_many_422(client, teacher_login):
    """Sprint 35: >50 materials → 422."""
    r = client.post(
        "/api/v1/teacher/materials/bulk-approve",
        json={"material_ids": list(range(1, 60))},
        headers={"Authorization": f"Bearer {teacher_login}"},
    )
    assert r.status_code == 422


def test_bulk_approve_non_teacher_403(client):
    """Sprint 35: только teacher/admin могут bulk-approve."""
    # Register student
    r = client.post(
        "/api/v1/auth/register",
        json={
            "email": "student@example.com",
            "password": "Kirill2026!",
            "display_name": "Student",
            "role": "student",
            "grade": 7,
        },
    )
    assert r.status_code == 201, f"Register failed: {r.status_code} {r.text}"
    student_token = client.post(
        "/api/v1/auth/login",
        json={"email": "student@example.com", "password": "Kirill2026!"},
    ).json()["access_token"]

    r = client.post(
        "/api/v1/teacher/materials/bulk-approve",
        json={"material_ids": [1]},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    # Sprint 35: student → 403 (require_teacher_or_admin).
    assert r.status_code == 403, f"Got {r.status_code} instead of 403"