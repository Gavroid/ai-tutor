"""Pilot Core Stage 1 — Phase 2: server-owned exercise instances (P1.2.2).

Проверяет, что:
- в `app/ai/models.py` есть SQLAlchemy-модель `GeneratedExerciseInstance`
  с полями: owner, topic, question, type, options, server-side reference
  (`correct_answer`), explanation, difficulty, model, prompt_version,
  created/expires, submission state;
- миграция `0013_generated_exercise_instances` существует и применяется;
- добавление новой строки не требует секретов;
- safe projection `to_safe_dict()` НЕ отдаёт `correct_answer`.

Это RED-тест перед реализацией: он падает, пока модель/миграция не созданы.
"""
from __future__ import annotations

import json
import os
import uuid

os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-for-pytest-only-1234567890")
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.ai.models import GeneratedExerciseInstance  # noqa: E402
from app.db.session import Base  # noqa: E402
from app.users.models import Role, User  # noqa: E402


def test_model_imports_and_has_required_columns():
    """P1.2.2 RED: GeneratedExerciseInstance должен быть импортируемым с правильными полями."""
    required_columns = {
        "id",
        "owner_id",
        "topic_id",
        "question_text",
        "type",
        "options_json",
        "correct_answer",
        "explanation",
        "difficulty",
        "model",
        "prompt_version",
        "created_at",
        "expires_at",
        "submitted_at",
        "submission_answer",
        "submission_score",
    }
    actual = set(GeneratedExerciseInstance.__table__.columns.keys())
    missing = required_columns - actual
    assert not missing, f"missing required columns: {missing}; have: {actual}"


def test_to_safe_dict_hides_correct_answer(db_session):
    """P1.2.2 RED: safe projection НЕ должна отдавать correct_answer, а только opaque id."""
    owner = User(
        email=f"student-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="x",
        display_name="Кирилл",
        role=Role.STUDENT,
    )
    db_session.add(owner)
    db_session.flush()

    e = GeneratedExerciseInstance(
        owner_id=owner.id,
        topic_id=2,
        question_text="2+2",
        type="numeric",
        options_json=None,
        correct_answer="4",
        explanation="two plus two",
        difficulty=1,
        model="mock",
        prompt_version="1",
    )
    db_session.add(e)
    db_session.flush()  # получаем реальный id

    safe = e.to_safe_dict()
    serialized = json.dumps(safe)
    assert "correct_answer" not in serialized, "safe projection must NOT include correct_answer"
    assert "explanation" not in serialized, "safe projection must NOT include explanation (only after submit)"
    # opaque identifier
    assert "exercise_id" in safe and isinstance(safe["exercise_id"], int) and safe["exercise_id"] > 0



def test_migration_0013_is_present():
    """P1.2.2: additive migration 0013_generated_exercise_instances must exist."""
    from pathlib import Path

    from app.config import get_settings

    Base.metadata.drop_all(_engine())
    Base.metadata.create_all(_engine())
    # Если модель импортирована и зарегистрирована — её таблица уже существует
    # после create_all. Дополнительно проверяем файл миграции.
    versions = Path(__file__).resolve().parent.parent / "alembic" / "versions"
    matches = list(versions.glob("0013_*.py"))
    assert matches, "expected migration file 0013_*.py"
    # Heuristic: migration должен создавать таблицу с похожим именем.
    text = matches[0].read_text()
    assert "generated_exercise_instances" in text


def _engine():
    eng = create_engine("sqlite+pysqlite:///:memory:", future=True)
    return eng


@pytest.fixture()
def db_session():
    eng = _engine()
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    SessionLocal = sessionmaker(bind=eng)
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()
        Base.metadata.drop_all(eng)


def test_create_and_fetch_instance(db_session):
    """P1.2.2 GREEN: создание/чтение строки работает, поля сохраняются как заданы."""
    owner = User(
        email=f"student-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="x",
        display_name="Кирилл",
        role=Role.STUDENT,
    )
    db_session.add(owner)
    db_session.flush()

    inst = GeneratedExerciseInstance(
        owner_id=owner.id,
        topic_id=1,
        question_text="Сколько будет 2+2?",
        type="numeric",
        options_json=None,
        correct_answer="4",
        explanation="Складываем 2 и 2",
        difficulty=1,
        model="mock",
        prompt_version="pilot-1",
    )
    db_session.add(inst)
    db_session.commit()

    fetched = db_session.scalar(
        select(GeneratedExerciseInstance).where(
            GeneratedExerciseInstance.owner_id == owner.id
        )
    )
    assert fetched is not None
    assert fetched.question_text == "Сколько будет 2+2?"
    assert fetched.correct_answer == "4"
    assert fetched.submitted_at is None
    assert fetched.submission_answer is None
