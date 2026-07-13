"""Sprint 9.2: multi-child тесты для родителя."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.auth.security import create_access_token
from app.db.session import Base, SessionLocal, engine
from app.main import app
from app.users import models as user_models
from app.users import service as user_service
from app.users.models import ParentStudentLink
from app.users.schemas import UserCreate
from sqlalchemy import select


@pytest.fixture()
def two_kids_parent():
    """Parent + 2 students + 1 revoked + 2 active parent_student_links."""
    Base.metadata.drop_all(engine)
    engine.dispose()
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        parent = user_service.register_user(
            db,
            UserCreate(
                email="parent@example.com",
                password="strongpass1",
                display_name="Папа",
                role="parent",
            ),
        )
        kid1 = user_service.register_user(
            db,
            UserCreate(
                email="kid1@example.com",
                password="strongpass1",
                display_name="Старший",
                role="student",
                grade=7,
            ),
        )
        kid2 = user_service.register_user(
            db,
            UserCreate(
                email="kid2@example.com",
                password="strongpass1",
                display_name="Младший",
                role="student",
                grade=7,
            ),
        )
        db.add(ParentStudentLink(parent_id=parent.id, student_id=kid1.id, status="active"))
        db.add(ParentStudentLink(parent_id=parent.id, student_id=kid2.id, status="active"))
        db.commit()
        token, _ = create_access_token(parent)
        # Capture IDs as plain ints BEFORE closing session
        return {
            "parent_id": parent.id,
            "parent_email": parent.email,
            "kid1_id": kid1.id,
            "kid2_id": kid2.id,
            "token": token,
        }
    finally:
        db.close()


class TestMultiChildList:
    """GET /api/v1/parents/children — список всех привязанных детей."""

    def test_returns_all_active_children(self, two_kids_parent):
        c = TestClient(app)
        token = two_kids_parent["token"]
        r = c.get("/api/v1/parents/children", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        items = r.json()
        assert len(items) == 2
        ids = {item["student_id"] for item in items}
        assert two_kids_parent["kid1_id"] in ids
        assert two_kids_parent["kid2_id"] in ids

    def test_excludes_revoked_links(self, two_kids_parent):
        # Отзываем связь с kid1
        db = SessionLocal()
        try:
            link = db.execute(
                select(ParentStudentLink).where(
                    ParentStudentLink.parent_id == two_kids_parent["parent_id"],
                    ParentStudentLink.student_id == two_kids_parent["kid1_id"],
                )
            ).scalar_one()
            link.status = "revoked"
            db.commit()
        finally:
            db.close()

        c = TestClient(app)
        r = c.get(
            "/api/v1/parents/children",
            headers={"Authorization": f"Bearer {two_kids_parent['token']}"},
        )
        assert r.status_code == 200
        items = r.json()
        assert len(items) == 1
        assert items[0]["student_id"] == two_kids_parent["kid2_id"]


class TestMultiChildPrivacy:
    """Privacy: 404 (не 403) если родитель запрашивает чужого ребёнка."""

    def test_unlinked_child_returns_404(self, two_kids_parent):
        """Чужой ребёнок → 404 (НЕ 403, чтобы не палить существование)."""
        # Создаём нового родителя без связей
        db = SessionLocal()
        try:
            other_parent = user_service.register_user(
                db,
                UserCreate(
                    email="intruder@example.com",
                    password="strongpass1",
                    display_name="Чужой",
                    role="parent",
                ),
            )
            db.commit()
            other_token, _ = create_access_token(other_parent)
        finally:
            db.close()

        c = TestClient(app)
        r = c.get(
            f"/api/v1/parents/students/{two_kids_parent['kid1_id']}/dashboard",
            headers={"Authorization": f"Bearer {other_token}"},
        )
        # 404 чтобы НЕ выдать существование студента
        assert r.status_code == 404

    def test_valid_child_returns_dashboard(self, two_kids_parent):
        """Свой ребёнок → дашборд 200."""
        c = TestClient(app)
        r = c.get(
            f"/api/v1/parents/students/{two_kids_parent['kid1_id']}/dashboard",
            headers={"Authorization": f"Bearer {two_kids_parent['token']}"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["student"]["id"] == two_kids_parent["kid1_id"]
        assert "subject_mastery" in body


class TestMultiChildAuth:
    """Только parent может запрашивать /parents/*. 401/403 для других ролей."""

    def test_student_role_forbidden(self):
        Base.metadata.drop_all(engine)
        engine.dispose()
        Base.metadata.create_all(engine)
        db = SessionLocal()
        try:
            student = user_service.register_user(
                db,
                UserCreate(
                    email="s@example.com",
                    password="strongpass1",
                    display_name="Студент",
                    role="student",
                    grade=7,
                ),
            )
            db.commit()
            tok, _ = create_access_token(student)
        finally:
            db.close()
        c = TestClient(app)
        r = c.get("/api/v1/parents/children", headers={"Authorization": f"Bearer {tok}"})
        # 401/403 — зависит от middleware
        assert r.status_code in (401, 403)

    def test_anonymous_unauthorized(self):
        c = TestClient(app)
        r = c.get("/api/v1/parents/children")
        assert r.status_code in (401, 403)
