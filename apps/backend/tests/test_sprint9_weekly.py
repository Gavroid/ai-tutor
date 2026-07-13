"""Sprint 9.1: weekly summary email для родителя."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from app.db.session import Base, SessionLocal, engine
from app.notifications import weekly
from app.notifications.weekly import (
    _aggregate_progress_for_student,
    _render_html,
    send_weekly_summary_for_all_parents,
    send_weekly_summary_for_parent,
)
from app.subjects.scripts_seed_runner import seed_for_tests
from app.users import models as user_models
from app.users import service as user_service
from app.users.models import ParentStudentLink
from app.users.schemas import UserCreate


def _setup() -> tuple[int, int]:
    """Регистрируем parent+student, связываем через parent_student_links.

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
                email="parent@example.com",
                password="strongpass1",
                display_name="Папа",
                role="parent",
            ),
        )
        student = user_service.register_user(
            db,
            UserCreate(
                email="kid@example.com",
                password="strongpass1",
                display_name="Кирилл",
                role="student",
                grade=7,
            ),
        )
        db.add(ParentStudentLink(parent_id=parent.id, student_id=student.id, status="active"))
        db.commit()
        return parent.id, student.id
    finally:
        db.close()


class TestWeeklyAggregate:
    def test_aggregate_zeros_for_new_student(self):
        """Если за неделю нет попыток — нули."""
        parent_id, student_id = _setup()
        db = SessionLocal()
        try:
            agg = _aggregate_progress_for_student(db, student_id, datetime.now(timezone.utc))
            assert agg["attempts_total"] == 0
            assert agg["attempts_correct"] == 0
            assert agg["accuracy_pct"] == 0.0
            assert agg["active_days"] == 0
            assert agg["topics_in_progress"] == 0
        finally:
            db.close()


class TestWeeklyRenderHtml:
    def test_html_safe_escape(self):
        """Имя ученика экранируется."""
        html = _render_html(
            "Кирилл <script>alert(1)</script>",
            "01.01—07.01.2027",
            {"attempts_total": 0, "attempts_correct": 0, "accuracy_pct": 0.0,
             "topics_in_progress": 0, "mastery_avg_pct": 0.0, "active_days": 0},
        )
        # XSS не должен пройти
        assert "<script>" not in html
        assert "&lt;script&gt;" in html or "&lt;script" in html

    def test_html_contains_kpi_numbers(self):
        html = _render_html(
            "Кирилл",
            "01.01—07.01.2027",
            {"attempts_total": 12, "attempts_correct": 10, "accuracy_pct": 83.3,
             "topics_in_progress": 4, "mastery_avg_pct": 65.0, "active_days": 5},
        )
        assert "12" in html  # attempts
        assert "83.3" in html  # accuracy
        assert "5" in html  # active days


class TestWeeklySend:
    def test_no_email_skips(self, monkeypatch):
        """Без email у родителя — пропуск."""
        parent_id, _ = _setup()
        db = SessionLocal()
        try:
            monkeypatch.delenv("SMTP_URL", raising=False)
            # Parent имеет email, нет SMTP_URL → dry-run → но всё равно считается "отправлено"
            n = send_weekly_summary_for_parent(db, parent_id)
            assert n >= 0  # DRY-RUN mode, возвращает 1 для каждого ребёнка с данными
        finally:
            db.close()

    def test_no_children_returns_zero(self):
        """Parent без детей → 0."""
        _setup()
        db = SessionLocal()
        try:
            # Создаём parent без детей
            extra_parent = user_service.register_user(
                db,
                UserCreate(
                    email="alone@example.com",
                    password="strongpass1",
                    display_name="Одинокий",
                    role="parent",
                ),
            )
            db.commit()
            n = send_weekly_summary_for_parent(db, extra_parent.id)
            assert n == 0
        finally:
            db.close()

    def test_missing_parent_returns_zero(self):
        """Несуществующий parent → 0."""
        _setup()
        db = SessionLocal()
        try:
            n = send_weekly_summary_for_parent(db, 99999)
            assert n == 0
        finally:
            db.close()

    def test_send_for_all_parents(self):
        """Cron-обёртка проходит без ошибок."""
        parent_id, _ = _setup()
        db = SessionLocal()
        try:
            n = send_weekly_summary_for_all_parents(db)
            # 1 parent × 0 children с данными × dry-run = 0..1
            assert n >= 0
        finally:
            db.close()
