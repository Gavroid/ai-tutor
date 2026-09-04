"""Sprint 3.20 — миграция 0026_parent_link_no_self.

Проверяет, что CHECK constraint применён к таблице parent_student_links.
Правило:
- status='active' AND parent_id == student_id → ЗАПРЕЩЕНО (IntegrityError)
- status='pending' AND parent_id == student_id → РАЗРЕШЕНО (placeholder для invite)

Это согласуется с by-design логикой create_invite_for_parent в
app/parents/service.py: создаётся pending с student_id=parent_id, accept_invite
обновляет до реального student_id и status='active'.

Без CHECK constraint можно создать active self-link → parent получает свой же
дашборд как «ребёнок» → утечка персональных данных.
"""
from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from app.db.session import Base, SessionLocal, engine
from app.users import service as user_service
from app.users.models import ParentStudentLink
from app.users.schemas import UserCreate


def _setup_users() -> tuple[int, int]:
    """Создаём parent + student через стандартный user_service.register_user.

    Returns:
        (parent_id, student_id)
    """
    Base.metadata.drop_all(engine)
    engine.dispose()
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        parent = user_service.register_user(
            db,
            UserCreate(
                email="parent-active-selflink@example.com",
                password="strongpass1",
                display_name="Папа",
                role="parent",
            ),
        )
        student = user_service.register_user(
            db,
            UserCreate(
                email="student-active-selflink@example.com",
                password="strongpass1",
                display_name="Кирилл",
                role="student",
                grade=7,
            ),
        )
        db.commit()
        return parent.id, student.id
    finally:
        db.close()


class TestParentLinkNoSelf:
    def test_normal_link_insert_succeeds(self):
        """INSERT валидной parent→student связи работает (sanity)."""
        parent_id, student_id = _setup_users()
        db = SessionLocal()
        try:
            db.add(ParentStudentLink(parent_id=parent_id, student_id=student_id, status="active"))
            db.commit()
            link = (
                db.query(ParentStudentLink)
                .filter_by(parent_id=parent_id, student_id=student_id, status="active")
                .one()
            )
            assert link.status == "active"
        finally:
            db.close()

    def test_pending_self_link_insert_succeeds(self):
        """INSERT pending self-link РАЗРЕШЁН (placeholder для invite).

        Это by-design: create_invite_for_parent создаёт pending ссылку
        с student_id=parent_id, accept_invite потом обновляет.
        """
        parent_id, _student_id = _setup_users()
        db = SessionLocal()
        try:
            db.add(ParentStudentLink(parent_id=parent_id, student_id=parent_id, status="pending"))
            db.commit()
            link = (
                db.query(ParentStudentLink)
                .filter_by(parent_id=parent_id, status="pending")
                .one()
            )
            assert link.status == "pending"
            assert link.student_id == parent_id  # placeholder
        finally:
            db.close()

    def test_active_self_link_insert_fails_with_integrity_error(self):
        """INSERT active self-link (parent_id == student_id, status='active') → IntegrityError.

        Без CHECK constraint такая вставка прошла бы (FK self-reference на users.id).
        С CHECK constraint — должна падать.
        """
        parent_id, _student_id = _setup_users()
        db = SessionLocal()
        try:
            with pytest.raises(IntegrityError) as exc:
                db.add(
                    ParentStudentLink(
                        parent_id=parent_id,
                        student_id=parent_id,
                        status="active",
                    )
                )
                db.commit()
            db.rollback()
            msg = str(exc.value).lower()
            assert "check" in msg or "constraint" in msg, (
                f"unexpected IntegrityError: {exc.value}"
            )
        finally:
            db.close()

    def test_pending_to_active_self_link_update_fails(self):
        """UPDATE pending self-link → status='active' → IntegrityError.

        Симулирует попытку «обмануть» систему: создать pending placeholder,
        потом попытаться перевести в active без accept_invite (без смены
        student_id). Должно падать.
        """
        parent_id, _student_id = _setup_users()
        db = SessionLocal()
        try:
            # Создаём pending placeholder
            link = ParentStudentLink(parent_id=parent_id, student_id=parent_id, status="pending")
            db.add(link)
            db.commit()
            db.refresh(link)

            # Пытаемся перевести в active (без смены student_id) → должно падать
            with pytest.raises(IntegrityError) as exc:
                link.status = "active"
                db.commit()
            db.rollback()
            msg = str(exc.value).lower()
            assert "check" in msg or "constraint" in msg, (
                f"unexpected IntegrityError: {exc.value}"
            )
        finally:
            db.close()
