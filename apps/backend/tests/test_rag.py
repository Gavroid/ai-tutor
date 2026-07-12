"""Тесты RAG chunking + cosine similarity + vector store."""
from __future__ import annotations

import os

os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-for-pytest-only-1234567890")
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")
os.environ.setdefault("AI_API_KEY", "mock-key-for-tests")
os.environ.pop("WHISPER_API_URL", None)

import pytest
from fastapi.testclient import TestClient

from app.db.session import Base, SessionLocal, engine, get_db
from app.main import app
from app.rag import (
    add_chunks,
    chunk_text,
    clear,
    cosine_similarity,
    get_embedding,
    search,
    stats,
)
from app.subjects import models as subj_models
from app.subjects.scripts_seed_runner import seed_for_tests
from app.users import service as user_service
from app.users.schemas import UserCreate


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    engine.dispose()
    Base.metadata.create_all(engine)

    s = SessionLocal()
    user_service.register_user(
        s,
        UserCreate(
            email="kid@x.com",
            password="strongpass1",
            display_name="Kid",
            role="student",
            grade=7,
        ),
    )
    # Seed full curriculum (12 subjects, sections, topics)
    seed_for_tests(s, reset=False)
    # Создаём material в первом доступном topic
    topic = s.query(subj_models.Topic).first()
    material = subj_models.LearningMaterial(
        topic_id=topic.id,
        title="Test Material",
        content="Дробь — это математическое понятие.",
    )
    s.add(material)
    s.commit()
    s.close()

    def _gen():
        s = SessionLocal()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = _gen
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


def _login(c: TestClient) -> str:
    r = c.post(
        "/api/v1/auth/login",
        json={"email": "kid@x.com", "password": "strongpass1"},
    )
    return r.json()["access_token"]


def test_chunk_text_splits_long():
    text = "A" * 1500
    chunks = chunk_text(text, chunk_size=500, overlap=50)
    assert len(chunks) > 1
    # Все чанки должны быть непустыми
    assert all(len(c) > 0 for c in chunks)
    # Объединение должно примерно соответствовать оригиналу
    assert sum(len(c) for c in chunks) >= len(text) - 100


def test_chunk_text_short_returns_single():
    text = "Короткий текст"
    chunks = chunk_text(text)
    assert chunks == ["Короткий текст"]


def test_chunk_text_empty():
    assert chunk_text("") == []
    assert chunk_text("   \n\n  ") == []


def test_cosine_similarity_identical():
    a = [0.1, 0.2, 0.3, 0.4]
    assert cosine_similarity(a, a) > 0.99


def test_cosine_similarity_orthogonal():
    a = [1.0, 0.0]
    b = [0.0, 1.0]
    assert abs(cosine_similarity(a, b)) < 0.01


def test_cosine_similarity_empty():
    assert cosine_similarity([], []) == 0.0
    assert cosine_similarity([1.0], [1.0, 2.0]) == 0.0


def test_hash_embedding_is_deterministic():
    """Без AI_API_KEY используется hash-based fallback."""
    os.environ["AI_API_KEY"] = ""
    e1 = get_embedding_sync("test text")
    e2 = get_embedding_sync("test text")
    assert e1 == e2  # одинаковый текст → одинаковый embedding
    e3 = get_embedding_sync("different text")
    assert e1 != e3


def get_embedding_sync(text: str) -> list[float]:
    import asyncio

    return asyncio.run(get_embedding(text))


def test_rag_search_finds_relevant():
    """После индексации, поиск находит релевантные чанки."""
    clear()
    # Индексируем документы
    chunks = [
        "Дробь — это математическое понятие",
        "Квадрат имеет четыре стороны",
        "Дробь состоит из числителя и знаменателя",
    ]
    import asyncio

    embeddings = [asyncio.run(get_embedding(c)) for c in chunks]
    add_chunks(material_id=1, chunks=chunks, embeddings=embeddings)

    # Ищем по "что такое дробь"
    query_emb = asyncio.run(get_embedding("что такое дробь"))
    results = search(query_emb, top_k=2)

    assert len(results) == 2
    # Топ-результаты должны быть про "дробь"
    texts = [r.text for r in results]
    assert any("дробь" in t.lower() for t in texts)


def test_rag_index_endpoint(client):
    """POST /rag/index создаёт chunks."""
    clear()
    token = _login(client)
    r = client.post(
        "/api/v1/rag/index",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "material_id": 1,
            "text": "Дробь — это математическое понятие. Дробь состоит из числителя и знаменателя.",
            "metadata": {"source": "test"},
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["indexed_chunks"] >= 1
    assert len(body["chunk_ids"]) == body["indexed_chunks"]


def test_rag_search_endpoint(client):
    """POST /rag/search возвращает релевантные чанки."""
    clear()
    token = _login(client)
    # Сначала индексируем
    client.post(
        "/api/v1/rag/index",
        headers={"Authorization": f"Bearer {token}"},
        json={"material_id": 1, "text": "Дробь — это математическое понятие"},
    )
    # Потом ищем
    r = client.post(
        "/api/v1/rag/search",
        headers={"Authorization": f"Bearer {token}"},
        json={"query": "дробь", "top_k": 3},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["query"] == "дробь"
    assert len(body["hits"]) >= 1


def test_rag_stats(client):
    """GET /rag/stats показывает статистику."""
    clear()
    token = _login(client)
    r = client.get(
        "/api/v1/rag/stats",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert "total_chunks" in body
    assert "total_materials" in body


def test_rag_requires_auth(client):
    """POST /rag/search без auth → 401."""
    r = client.post("/api/v1/rag/search", json={"query": "test"})
    assert r.status_code == 401
