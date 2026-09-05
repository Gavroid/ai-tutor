"""Sprint 3.43 P1: regression test для production bug в prompts.py:313.

БАГ: `from app.rag_models import LearningMaterial, RagChunk` — LearningMaterial
живёт в `app.subjects.models`, не в `app.rag_models`. ImportError на каждом
вызове _get_rag_context_for_topic, глотается через `except Exception: return ""`.
RAG-контекст в generate_exercise (P11) молча мёртв — функция возвращает "".

Найдено независимым аудитом 2026-09-05 (`14-independent-audit-2026-09-05.md`).
Тот же класс бага, что и AIMessage из Sprint 3.36a.

Подход к изоляции БД:
- Используем ОТДЕЛЬНЫЙ engine per-test модуль через StaticPool in-memory.
- Это полностью изолирует наши данные от module-level engine в app.db.session,
  и от drop_all/create_all в других тестах (test_sprint16_register и т.д.).
- monkeypatch подменяет SessionLocal в app.db.session чтобы _get_rag_context_for_topic
  использовал нашу test engine.
"""

from __future__ import annotations

import uuid

import pytest
from app.ai.prompts import _get_rag_context_for_topic
from app.db.session import Base
from app.rag_models import RagChunk
from app.rag_persist import chunk_hash
from app.subjects import models as subj_models
from app.subjects.models import LearningMaterial
from app.users import models as user_models
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Sprint 3.43 P1: отдельный engine чтобы избежать race с другими тестами.
_test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Base.metadata.create_all(_test_engine)
_TestSessionLocal = sessionmaker(bind=_test_engine)


def _create_topic_with_chunk(text: str, slug: str) -> int:
    """Создаёт user/subject/section/topic/material/chunk в изолированной БД."""
    unique_slug = f"{slug}-{uuid.uuid4().hex[:8]}"
    session = _TestSessionLocal()
    try:
        user = user_models.User(
            email=f"{unique_slug}@example.com",
            password_hash="x",
            role=user_models.Role.STUDENT,
            display_name="Test User",
        )
        session.add(user)
        session.flush()

        subject = subj_models.Subject(name=f"Test {unique_slug}", code=unique_slug, is_active=True)
        session.add(subject)
        session.flush()

        section = subj_models.Section(subject_id=subject.id, name="S", order_index=1)
        session.add(section)
        session.flush()

        topic = subj_models.Topic(section_id=section.id, name="T", order_index=1)
        session.add(topic)
        session.flush()

        material = LearningMaterial(
            topic_id=topic.id,
            title="M",
            content="C",
            status="published",
        )
        session.add(material)
        session.flush()

        chunk = RagChunk(
            material_id=material.id,
            text=text,
            hash=chunk_hash(material.id, text),
        )
        session.add(chunk)
        session.commit()
        return topic.id
    finally:
        session.close()


def _create_empty_topic(slug: str) -> int:
    """Создаёт user/subject/section/topic без material/chunk."""
    unique_slug = f"{slug}-{uuid.uuid4().hex[:8]}"
    session = _TestSessionLocal()
    try:
        user = user_models.User(
            email=f"{unique_slug}@example.com",
            password_hash="x",
            role=user_models.Role.STUDENT,
            display_name="Test User",
        )
        session.add(user)
        session.flush()

        subject = subj_models.Subject(name=f"Test {unique_slug}", code=unique_slug, is_active=True)
        session.add(subject)
        session.flush()

        section = subj_models.Section(subject_id=subject.id, name="S", order_index=1)
        session.add(section)
        session.flush()

        topic = subj_models.Topic(section_id=section.id, name="T", order_index=1)
        session.add(topic)
        session.commit()
        return topic.id
    finally:
        session.close()


@pytest.fixture(autouse=True)
def _patch_session_local(monkeypatch):
    """Sprint 3.43 P1: подменяет SessionLocal чтобы _get_rag_context_for_topic
    использовал наш test engine (а не module-level).

    Без этого данные созданные в _test_engine невидимы для функции.
    """
    monkeypatch.setattr("app.db.session.SessionLocal", _TestSessionLocal)


class TestRagContextForTopicRegression:  # noqa: E801
    """Sprint 3.43 P1: verify _get_rag_context_for_topic не падает молча."""

    def test_no_topic_id_returns_empty(self) -> None:
        """Без topic_id — пустая строка (existing behavior)."""
        assert _get_rag_context_for_topic(None) == ""

    def test_returns_first_sentence_when_chunk_exists(self) -> None:
        """RAG-контекст возвращает первое содержательное предложение (>= 40 chars)."""
        long_text = (
            "Это первое содержательное предложение из реального учебника, "
            "которое должно вернуться функцией _get_rag_context_for_topic. "
            "Второе предложение игнорируется."
        )
        topic_id = _create_topic_with_chunk(long_text, "test-rag-p11-context")

        result = _get_rag_context_for_topic(topic_id)

        assert result, (
            "🚨 P1 BUG: _get_rag_context_for_topic вернул пустую строку, "
            "хотя chunk существует. Это значит bug prompts.py:313 "
            "(import LearningMaterial from wrong module) НЕ починен."
        )
        assert "первое содержательное предложение" in result
        assert len(result) <= 400

    def test_no_chunk_returns_empty(self) -> None:
        """Если chunk'ов нет — пустая строка (existing correct behavior)."""
        topic_id = _create_empty_topic("test-rag-p11-nochunk")

        result = _get_rag_context_for_topic(topic_id)

        assert result == ""

    def test_smoke_existing_data_does_not_return_empty(self) -> None:
        """Sprint 3.43 P1: главный smoke test для бага.

        Если у topic_id есть материал и chunk — функция НЕ возвращает ""
        (иначе P11 RAG-context в generate_exercise молча мёртв).
        """
        topic_id = _create_topic_with_chunk(
            "Достаточно длинный текст чтобы пройти фильтр >= 40 символов и вернуть предложение пользователю.",
            "test-rag-p11-smoke",
        )

        result = _get_rag_context_for_topic(topic_id)

        assert result, "🚨 P1 BUG: RAG-контекст пустой — generate_exercise " "теряет контекст реального учебника."
