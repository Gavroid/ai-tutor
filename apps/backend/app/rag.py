"""Простой RAG (Retrieval Augmented Generation).

Стратегия:
1. При загрузке материала через /materials/upload — режем текст на чанки по 500 chars
2. Генерируем embedding для каждого чанка (OpenAI-compatible API)
3. Сохраняем в простую "in-memory vector store" (для MVP)
4. При AI запросе — находим топ-3 релевантных чанка и добавляем в контекст

Для production: заменить на pgvector / Qdrant / FAISS.
"""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from typing import Optional

import httpx


# === Embedding provider ===

async def get_embedding(text: str) -> list[float]:
    """Генерирует embedding через OpenAI-compatible API."""
    base_url = os.environ.get("AI_BASE_URL", "https://api.openrouter.ai/api/v1").rstrip("/")
    api_key = os.environ.get("AI_API_KEY", "").strip()
    model = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small")

    if not api_key:
        # Fallback: hash-based pseudo-embedding (для тестов без API key)
        return _hash_embedding(text, dim=384)

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": model, "input": text[:8000]}

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(f"{base_url}/embeddings", headers=headers, json=payload)
        if r.status_code != 200:
            # Fallback на hash
            return _hash_embedding(text, dim=384)
        data = r.json()
        # Поддержка разных форматов API
        if "data" in data and isinstance(data["data"], list) and data["data"]:
            return data["data"][0].get("embedding") or _hash_embedding(text, dim=384)
        if "embedding" in data:
            return data["embedding"]
        # Неожиданный формат — fallback
        return _hash_embedding(text, dim=384)


def _hash_embedding(text: str, dim: int = 384) -> list[float]:
    """Детерминированный псевдо-embedding (для тестов).

    Не настоящий embedding, но стабильный для одинакового текста.
    """
    text_normalized = text.lower().strip()
    # Use SHA-256 для стабильности
    h = hashlib.sha256(text_normalized.encode()).digest()
    vec = []
    for i in range(dim):
        # Берём 4 байта из hash (rolling)
        b = h[(i * 4) % len(h):(i * 4) % len(h) + 4].ljust(4, b'\x00')
        val = int.from_bytes(b, "big", signed=False)
        # Нормализуем в [-1, 1]
        vec.append((val / 2**31) - 1.0)
    # L2 нормализация
    norm = sum(v * v for v in vec) ** 0.5
    if norm > 0:
        vec = [v / norm for v in vec]
    return vec


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity между двумя векторами."""
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


# === Chunking ===

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Режет текст на чанки с overlap."""
    text = text.strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        # Граница по предложению если возможно
        if end < len(text):
            for sep in [". ", "! ", "? ", "\n\n", "\n"]:
                pos = text.rfind(sep, start + chunk_size // 2, end)
                if pos != -1:
                    end = pos + len(sep)
                    break

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end - overlap
        if start < 0:
            start = 0

    return chunks


# === Vector store (in-memory для MVP) ===

@dataclass
class DocumentChunk:
    id: str
    material_id: int
    text: str
    embedding: list[float]
    metadata: dict


# Глобальное хранилище (для MVP — в памяти)
_store: dict[str, DocumentChunk] = {}


def add_chunks(material_id: int, chunks: list[str], embeddings: list[list[float]], metadata: dict | None = None) -> list[str]:
    """Добавляет чанки в хранилище, возвращает их ID."""
    ids = []
    for text, emb in zip(chunks, embeddings):
        cid = hashlib.sha256(f"{material_id}:{text}".encode()).hexdigest()[:16]
        _store[cid] = DocumentChunk(
            id=cid,
            material_id=material_id,
            text=text,
            embedding=emb,
            metadata=metadata or {},
        )
        ids.append(cid)
    return ids


def remove_by_material(material_id: int) -> int:
    """Удаляет все чанки материала."""
    to_remove = [cid for cid, c in _store.items() if c.material_id == material_id]
    for cid in to_remove:
        del _store[cid]
    return len(to_remove)


def search(query_embedding: list[float], top_k: int = 3, material_id: Optional[int] = None) -> list[DocumentChunk]:
    """Находит top_k релевантных чанков."""
    candidates = _store.values()
    if material_id is not None:
        candidates = [c for c in candidates if c.material_id == material_id]

    if not candidates:
        return []

    scored = [(cosine_similarity(query_embedding, c.embedding), c) for c in candidates]
    scored.sort(key=lambda x: -x[0])
    return [c for _, c in scored[:top_k]]


def clear() -> int:
    """Очищает весь store."""
    count = len(_store)
    _store.clear()
    return count


def stats() -> dict:
    """Статистика store."""
    return {
        "total_chunks": len(_store),
        "total_materials": len({c.material_id for c in _store.values()}),
    }
