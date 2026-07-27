"""Sprint 71: real embeddings search tests."""
from __future__ import annotations

import os

os.environ.setdefault("OTEL_SDK_DISABLED", "true")

import json

import pytest
from fastapi.testclient import TestClient


# === Module-level tests (без DB) ===

def test_search_real_persistent_imports():
    """Sprint 71: search_real_persistent module imports."""
    from app.rag_persist import search_real_persistent

    assert callable(search_real_persistent)


def test_search_real_endpoint_registered():
    """Sprint 71: /api/v1/rag/search/real endpoint registered."""
    from app.main import app

    paths = [getattr(route, "path", str(route)) for route in app.routes]
    assert "/api/v1/rag/search/real" in paths


# === Real search tests ===

@pytest.fixture
def client():
    """Sprint 71: TestClient + DB setup."""
    from app.db.session import engine, Base
    from app.main import app

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    return TestClient(app)


@pytest.fixture
def user_token(client):
    """Sprint 71: student token."""
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


def _add_test_chunks_with_real_embeddings():
    """Helper: добавить test chunks с real embeddings."""
    from app.db.session import SessionLocal
    from app.rag_embeddings import encode_texts
    from app.rag_persist import add_chunks_persistent
    from app.rag_models import RagChunk

    texts = [
        "Формула площади круга: S = π × r²",
        "Теорема Пифагора: a² + b² = c²",
        "Фотография — это искусство запечатления момента",
        "График функции y = x² — парабола",
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
def test_search_real_returns_relevant_chunks(client, user_token):
    """Sprint 71: real search возвращает relevant chunks."""
    _add_test_chunks_with_real_embeddings()

    r = client.post(
        "/api/v1/rag/search/real",
        json={"query": "площадь круга", "top_k": 3},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data["hits"]) > 0
    top_text = data["hits"][0]["text"].lower()
    assert "площад" in top_text or "круг" in top_text, f"Top hit: {top_text}"


@pytest.mark.slow
def test_search_real_filters_by_material_id(client, user_token):
    """Sprint 71: search_real filter by material_id."""
    from app.db.session import SessionLocal
    from app.rag_embeddings import encode_texts
    from app.rag_persist import add_chunks_persistent

    # Use unique material_ids чтобы не пересекаться с другими тестами
    texts = ["Текст для материала 100", "Текст для материала 200"]
    embeddings = encode_texts(texts)
    assert embeddings is not None

    with SessionLocal() as db:
        add_chunks_persistent(
            db,
            material_id=100,
            chunks=[texts[0]],
            embeddings=[embeddings[0].tolist()],
            metadata={
                "topic_id": 100,
                "material_title": "Math 100",
                "embedding_v2": embeddings[0].tolist(),
                "embedding_model": "paraphrase-multilingual-MiniLM-L12-v2",
                "embedding_dim": 384,
            },
        )
        add_chunks_persistent(
            db,
            material_id=200,
            chunks=[texts[1]],
            embeddings=[embeddings[1].tolist()],
            metadata={
                "topic_id": 200,
                "material_title": "Math 200",
                "embedding_v2": embeddings[1].tolist(),
                "embedding_model": "paraphrase-multilingual-MiniLM-L12-v2",
                "embedding_dim": 384,
            },
        )

    r = client.post(
        "/api/v1/rag/search/real",
        json={"query": "текст", "top_k": 5, "material_id": 100},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert r.status_code == 200
    hits = r.json()["hits"]
    for h in hits:
        assert h["material_id"] == 100


@pytest.mark.slow
def test_search_real_skips_chunks_without_embeddings(client, user_token):
    """Sprint 71: chunks without embedding_v2 пропускаются."""
    from app.db.session import SessionLocal
    from app.rag_persist import add_chunks_persistent

    with SessionLocal() as db:
        # Chunk without embedding_v2 (only hash-based)
        add_chunks_persistent(
            db,
            material_id=1,
            chunks=["Old chunk without real embeddings"],
            embeddings=[[0.0] * 384],  # fake embedding
            metadata={
                "topic_id": 1,
                "material_title": "Old Chunk",
                # NO embedding_v2
            },
        )

    r = client.post(
        "/api/v1/rag/search/real",
        json={"query": "test", "top_k": 5},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert r.status_code == 200
    # Should return empty (no real embeddings)
    assert r.json()["hits"] == []


def test_search_real_requires_auth(client):
    """Sprint 71: /search/real требует auth."""
    r = client.post(
        "/api/v1/rag/search/real",
        json={"query": "test", "top_k": 3},
    )
    assert r.status_code == 401
