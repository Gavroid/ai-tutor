"""Sprint 3.5.2: integration тесты RAG в hot path.

Проверяют что app/ai/service.py::_build_rag_context корректно:
- возвращает None если RAG store пуст
- возвращает форматированный контекст если есть chunk'и
- не падает если RAG ломается (graceful degradation через try/except)
"""
from __future__ import annotations

import os

import pytest

os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-for-pytest-only-1234567890")
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")
os.environ.setdefault("AI_API_KEY", "mock-key-for-tests")
os.environ.setdefault("UPLOAD_DIR", "/tmp/ai-tutor-test-uploads")
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")

from app.ai import service as ai_service
import app.rag as rag_mod


class FakeSubject:
    def __init__(self, name: str = "Математика"):
        self.name = name


class FakeSection:
    def __init__(self, subject: FakeSubject):
        self.subject = subject


class FakeTopic:
    """Mock для app.subjects.models.Topic — только нужные поля."""
    def __init__(self, name: str, subject_name: str = "Математика"):
        self.name = name
        self.section = FakeSection(FakeSubject(subject_name))


class FakeProvider:
    """Mock для AIProvider — нам не нужно делать реальные вызовы."""
    async def complete(self, req):
        return None


@pytest.fixture
def db_session():
    """Sprint 3.5.2: persistent RAG работает через БД. Тесты используют SQLite."""
    from app.db.session import Base, engine
    # Create tables (rag_chunks + все из Base.metadata) на чистой SQLite.
    Base.metadata.create_all(engine)
    from app.db.session import SessionLocal
    session = SessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture(autouse=True)
def clear_rag_store(db_session):
    """Очищает in-memory + persistent store перед каждым тестом."""
    rag_mod.clear()
    try:
        from app.rag_models import RagChunk
        from sqlalchemy import delete
        db_session.execute(delete(RagChunk))
        db_session.commit()
    except Exception:
        db_session.rollback()
    yield
    rag_mod.clear()
    try:
        from app.rag_models import RagChunk
        from sqlalchemy import delete
        db_session.execute(delete(RagChunk))
        db_session.commit()
    except Exception:
        db_session.rollback()


@pytest.mark.asyncio
async def test_rag_context_empty_store_returns_none():
    """Если RAG-база пустая — context=None, AI отвечает "из головы"."""
    svc = ai_service.AIService(FakeProvider())
    topic = FakeTopic("Площадь треугольника")
    # Sprint 4.1.3: _build_rag_context возвращает (context_str, sources)
    ctx, sources = await svc._build_rag_context(None, topic)
    assert ctx is None
    assert sources == []


@pytest.mark.asyncio
async def test_rag_context_with_chunks(db_session):
    """Если в store есть chunk'и — context содержит их текст + meta."""
    # Sprint 3.5.2: пишем в persistent (rag_chunks), не in-memory.
    from app.rag_persist import add_chunks_persistent, get_or_compute_embedding
    emb = get_or_compute_embedding("Площадь треугольника 7 класс")
    add_chunks_persistent(
        db_session,
        material_id=999,
        chunks=["Площадь треугольника равна половине произведения основания на высоту."],
        embeddings=[emb],
        metadata={"material_title": "Геометрия 7 класс (учебник)", "page_number": 73},
    )

    svc = ai_service.AIService(FakeProvider())
    topic = FakeTopic("Площадь треугольника")
    # Sprint 4.1.3: _build_rag_context возвращает (context_str, sources)
    ctx, sources = await svc._build_rag_context(None, topic, top_k=3)

    assert ctx is not None
    assert "Геометрия 7 класс" in ctx
    assert "стр. 73" in ctx
    assert "основания на высоту" in ctx
    # sources тоже заполнены
    assert len(sources) >= 1
    assert sources[0]["material_title"] == "Геометрия 7 класс (учебник)"
    assert sources[0]["page_number"] == 73


@pytest.mark.asyncio
async def test_rag_context_failure_does_not_crash(monkeypatch):
    """Если RAG падает (исключение) — context=None, не валит explain_topic."""
    # Подменяем get_or_compute_embedding (используется внутри get_embedding)
    # чтобы он бросал исключение. Это ближе к реальной ошибке RAG.
    from app.rag_persist import get_or_compute_embedding as real_fn

    async def broken_get_or_compute(*args, **kwargs):
        raise RuntimeError("Embedding API down")

    # Подменяем в rag_persist (где функция определена).
    # Sprint 4.1.3: _build_rag_context делает local `from app.rag_persist import ...`,
    # поэтому нужно подменить в обоих местах — иначе local import "затенит" подмену.
    import app.rag_persist
    monkeypatch.setattr(app.rag_persist, "get_or_compute_embedding", broken_get_or_compute)
    # Также подменяем в sys.modules['app.ai.service'] (где _build_rag_context делает
    # свой local import). Но проще подменить в обоих через setattr после local import —
    # это требует monkeypatching через test runner. Используем side_effect чтобы бросать
    # исключение сразу:
    monkeypatch.setattr("app.ai.service.get_or_compute_embedding", broken_get_or_compute, raising=False)

    svc = ai_service.AIService(FakeProvider())
    topic = FakeTopic("Любая тема")
    # Должен вернуть None, не бросить исключение
    # Sprint 4.1.3: _build_rag_context возвращает (context_str, sources)
    ctx, sources = await svc._build_rag_context(None, topic)
    assert ctx is None
    assert sources == []


@pytest.mark.asyncio
async def test_rag_context_query_includes_subject_and_topic(db_session):
    """Query для retrieval = subject_name + topic_name (для точности)."""
    from app.rag_persist import add_chunks_persistent, get_or_compute_embedding
    emb = get_or_compute_embedding("Квадратные уравнения Алгебра")
    add_chunks_persistent(
        db_session,
        material_id=1,
        chunks=["Квадратные уравнения: Алгебра, дискриминант, корни."],
        embeddings=[emb],
        metadata={"material_title": "Алгебра 7 класс"},
    )

    svc = ai_service.AIService(FakeProvider())
    topic = FakeTopic("Квадратные уравнения", "Алгебра")
    # Sprint 4.1.3: _build_rag_context возвращает (context_str, sources)
    ctx, sources = await svc._build_rag_context(None, topic, top_k=3)

    assert ctx is not None
    assert "Квадратные уравнения" in ctx
    assert "Алгебра" in ctx
