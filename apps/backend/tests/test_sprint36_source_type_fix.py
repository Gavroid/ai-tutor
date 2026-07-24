"""Sprint 36.1: source_type='pdf' bug fix tests.

Проверяем:
- SourceType Literal теперь включает 'pdf'
- Pydantic сериализация работает для pdf материалов
- GET /teacher/materials возвращает 200 (не 500)
- Schema работает для всех 4 source_type значений
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
def teacher_login(client):
    """Sprint 36.1: teacher через прямой SQL (НЕ /auth/register — 403)."""
    from sqlalchemy.orm import Session
    from app.db.session import engine
    from app.users.models import User, Role
    from app.auth.security import hash_password

    with Session(engine) as db:
        user = User(
            email="teacher@example.com",
            password_hash=hash_password("Kirill2026!"),
            display_name="Teacher",
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


def test_source_type_literal_includes_pdf():
    """Sprint 36.1: SourceType Literal включает 'pdf'."""
    from app.teacher.schemas import SourceType

    # Compile-time проверка через typing.get_args
    import typing

    args = typing.get_args(SourceType)
    assert "pdf" in args, f"Expected 'pdf' in {args}"
    assert "text" in args
    assert "file" in args
    assert "topic" in args


def test_material_list_item_accepts_pdf_source(client, teacher_login):
    """Sprint 36.1: MaterialListItem принимает source_type='pdf'."""
    from app.db.session import SessionLocal
    from app.subjects.models import Subject, Section, Topic, LearningMaterial
    from jose import jwt
    from app.config import get_settings

    s = get_settings()
    user_id = int(jwt.get_unverified_claims(teacher_login)["sub"])

    with SessionLocal() as db:
        # Минимальный topic
        subject = Subject(code="math", name="Math")
        db.add(subject); db.flush()
        section = Section(subject_id=subject.id, name="Alg")
        db.add(section); db.flush()
        topic = Topic(section_id=section.id, name="Test", order_index=1)
        db.add(topic); db.flush()

        # Material с source_type='pdf' (тот самый проблемный случай)
        mat = LearningMaterial(
            generated_by=user_id,
            topic_id=topic.id,
            title="PDF Material",
            content="c",
            status="ai_generated",
            source_type="pdf",  # Sprint 36.1: было 500, теперь OK
        )
        db.add(mat); db.commit()

    # GET /teacher/materials — должно вернуть 200 (раньше 500)
    r = client.get(
        "/api/v1/teacher/materials",
        headers={"Authorization": f"Bearer {teacher_login}"},
    )
    assert r.status_code == 200, f"Got {r.status_code}: {r.text}"
    data = r.json()
    assert len(data) == 1
    assert data[0]["title"] == "PDF Material"
    assert data[0]["source_type"] == "pdf"


def test_material_list_item_accepts_all_source_types(client, teacher_login):
    """Sprint 36.1: все 4 source_type значения работают."""
    from app.db.session import SessionLocal
    from app.subjects.models import Subject, Section, Topic, LearningMaterial
    from jose import jwt
    from app.config import get_settings

    s = get_settings()
    user_id = int(jwt.get_unverified_claims(teacher_login)["sub"])

    with SessionLocal() as db:
        subject = Subject(code="math", name="Math")
        db.add(subject); db.flush()
        section = Section(subject_id=subject.id, name="Alg")
        db.add(section); db.flush()
        topic = Topic(section_id=section.id, name="Test", order_index=1)
        db.add(topic); db.flush()

        for st in ["text", "file", "topic", "pdf"]:
            mat = LearningMaterial(
                generated_by=user_id,
                topic_id=topic.id,
                title=f"Material {st}",
                content="c",
                status="ai_generated",
                source_type=st,
            )
            db.add(mat)
        db.commit()

    r = client.get(
        "/api/v1/teacher/materials",
        headers={"Authorization": f"Bearer {teacher_login}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 4
    source_types = {m["source_type"] for m in data}
    assert source_types == {"text", "file", "topic", "pdf"}


def test_material_list_with_search_works_after_fix(client, teacher_login):
    """Sprint 36.1: search + pdf materials работает."""
    from app.db.session import SessionLocal
    from app.subjects.models import Subject, Section, Topic, LearningMaterial
    from jose import jwt
    from app.config import get_settings

    s = get_settings()
    user_id = int(jwt.get_unverified_claims(teacher_login)["sub"])

    with SessionLocal() as db:
        subject = Subject(code="math", name="Math")
        db.add(subject); db.flush()
        section = Section(subject_id=subject.id, name="Alg")
        db.add(section); db.flush()
        topic = Topic(section_id=section.id, name="Test", order_index=1)
        db.add(topic); db.flush()

        # 2 pdf материала + 1 text
        for title, st in [
            ("Algebra PDF 1", "pdf"),
            ("Algebra PDF 2", "pdf"),
            ("Geometry text", "text"),
        ]:
            mat = LearningMaterial(
                generated_by=user_id,
                topic_id=topic.id,
                title=title,
                content="c",
                status="ai_generated",
                source_type=st,
            )
            db.add(mat)
        db.commit()

    # search=algebra — должно найти 2 (PDF материалы, не 500!)
    r = client.get(
        "/api/v1/teacher/materials?search=algebra",
        headers={"Authorization": f"Bearer {teacher_login}"},
    )
    assert r.status_code == 200, f"Got {r.status_code}: {r.text}"
    data = r.json()
    assert len(data) == 2
    titles = {m["title"] for m in data}
    assert "Algebra PDF 1" in titles
    assert "Algebra PDF 2" in titles