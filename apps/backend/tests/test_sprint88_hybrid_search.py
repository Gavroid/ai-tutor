"""Sprint 88: hybrid BM25 + real embeddings search tests."""
from __future__ import annotations

import os

os.environ.setdefault("OTEL_SDK_DISABLED", "true")

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Sprint 88: TestClient + DB setup."""
    from app.db.session import engine, Base
    from app.main import app

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    return TestClient(app)


@pytest.fixture
def user_token(client):
    """Sprint 88: student token."""
    from sqlalchemy.orm import Session
    from app.db.session import engine
    from app.users.models import User, Role
    from app.auth.security import hash_password

    with Session(engine) as db:
        user = User(
            email="user@example.com",
            password_hash=hash_password("Kirill2026!"),
            display_name="User",
            role=Role.STUDENT,
            is_active=True,
        )
        db.add(user)
        db.commit()

    r = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "Kirill2026!"},
    )
    return r.json()["access_token"]


# === Module tests ===

def test_search_hybrid_persistent_imports():
    """Sprint 88: search_hybrid_persistent module imports."""
    from app.rag_persist import search_hybrid_persistent

    assert callable(search_hybrid_persistent)


def test_hybrid_endpoint_registered(client):
    """Sprint 88: /api/v1/rag/search/hybrid endpoint registered."""
    from app.main import app

    paths = [getattr(route, "path", str(route)) for route in app.routes]
    assert "/api/v1/rag/search/hybrid" in paths


# === Real integration tests ===

def _add_test_chunks_with_both_embeddings():
    """Helper: добавить test chunks с BM25 keyword + real embeddings."""
    from app.db.session import SessionLocal
    from app.rag_embeddings import encode_texts
    from app.rag_persist import add_chunks_persistent

    texts = [
        "Площадь круга вычисляется через радиус",
        "Фотография — это искусство запечатления момента",
        "График функции — это парабола",
    ]
    embeddings = encode_texts(texts)
    assert embeddings is not None

    with SessionLocal() as db:
        for i, (t, emb) in enumerate(zip(texts, embeddings)):
            add_chunks_persistent(
                db,
                material_id=i + 1,
                chunks=[t],
                embeddings=[emb.tolist()],
                metadata={
                    "topic_id": i + 1,
                    "material_title": f"Material {i + 1}",
                    "embedding_v2": emb.tolist(),
                    "embedding_model": "paraphrase-multilingual-MiniLM-L12-v2",
                    "embedding_dim": 384,
                },
            )


@pytest.mark.slow
def test_hybrid_search_returns_relevant_chunks(client, user_token):
    """Sprint 88: hybrid search возвращает relevant chunks."""
    _add_test_chunks_with_both_embeddings()

    r = client.post(
        "/api/v1/rag/search/hybrid",
        json={"query": "площадь круга", "top_k": 3},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data["hits"]) > 0


@pytest.mark.slow
def test_hybrid_search_requires_auth(client):
    """Sprint 88: /search/hybrid требует auth."""
    r = client.post(
        "/api/v1/rag/search/hybrid",
        json={"query": "test", "top_k": 3},
    )
    assert r.status_code == 401


@pytest.mark.slow
def test_hybrid_search_fallback_without_embeddings(client, user_token, monkeypatch):
    """Sprint 88: если sentence-transformers unavailable → BM25 only (не crash).

    Sprint 101: is_available теперь module-level в rag_router,
    поэтому monkeypatch работает.
    """
    monkeypatch.setattr("app.rag_router.is_available", lambda: False)

    r = client.post(
        "/api/v1/rag/search/hybrid",
        json={"query": "площадь", "top_k": 3},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    # BM25 должен работать (не требует embeddings)
    assert r.status_code == 200
    data = r.json()
    assert "hits" in data