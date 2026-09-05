"""Sprint 3.29: _build_rag_context body moved from AIService.

Behavioral identity (zero change). Подход function-based extraction:
функция принимает 'service' (AIService instance) как первый аргумент.
Public API: AIService._build_rag_context остался через 1-line forwarding.
"""

from __future__ import annotations

import logging

from app.ai.service import _dedupe_rag_sources, _rag_enabled_for_subject
from app.subjects import models as subj_models
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


async def build_rag_context(
    service, db: Session, topic: subj_models.Topic, top_k: int = 3
) -> tuple[str | None, list[dict]]:
    """Sprint 3.5.2 + 4.1.3: RAG — топ-K chunk'ов из загруженных учебников.

    Returns:
        (context_str, sources_list) — текст для system prompt + список источников
        для UI (Sprint 4.1.3 — индикатор "📖 Источник").
        context_str = None если RAG пуст (не ошибка, сигнал "материалов по теме нет").
        sources_list = [{"material_title", "page_number", "chunk_id"}, ...]

    Использует hash-based pseudo-embedding (без расходов на embedding API).
    Sprint 3.5.2: persistent search через app.rag_persist.search_persistent
    (читает из rag_chunks в PostgreSQL). RAG-база переживает рестарт backend.
    """
    from app.rag_persist import get_or_compute_embedding, search_persistent

    subject = topic.section.subject
    if not _rag_enabled_for_subject(subject.name):
        return None, []
    # Sprint 3.5.2 + MVP rescue: RAG только для предмета, где материалы реально загружены.
    query = f"{topic.name} {topic.section.subject.name}"
    try:
        query_emb = get_or_compute_embedding(query)
        # Sprint 3.5.2: persistent search через PostgreSQL rag_chunks.
        # Используем db сессию через SessionLocal (self-contained).
        from app.db.session import SessionLocal
        from app.subjects.models import LearningMaterial

        with SessionLocal() as db:
            topic_id = getattr(topic, "id", None)
            material_ids = []
            if topic_id is not None:
                material_ids = [
                    row[0] for row in db.query(LearningMaterial.id).filter(LearningMaterial.topic_id == topic_id).all()
                ]
            chunks = []
            if material_ids:
                for material_id in material_ids:
                    chunks.extend(search_persistent(db, query_emb, top_k=top_k, material_id=material_id))
            else:
                # Persistent RAG can hold imported/book chunks without a LearningMaterial row.
                # Search globally, then trust metadata when present.
                chunks.extend(search_persistent(db, query_emb, top_k=top_k))
            filtered = []
            for chunk in chunks:
                metadata = getattr(chunk, "metadata", {}) or {}
                chunk_topic_id = metadata.get("topic_id")
                if topic_id is not None and chunk_topic_id is not None and chunk_topic_id != topic_id:
                    continue
                filtered.append(chunk)
            chunks = filtered[:top_k]
    except Exception as e:
        logger.warning("RAG search failed: %s", e)
        return None, []

    if not chunks:
        return None, []

    # Sprint C1 (2026-08-23): subject-keyword safety net.
    # Если material_title содержит слово из ДРУГОГО предмета (география
    # для math-topic), отбрасываем этот chunk. Это защищает ребёнка
    # от RAG routing bug: например, для math-6 «Среднее арифметическое»
    # привязан material «География — Реки и озёра».
    subject_name = (subject.name or "").lower() if subject else ""
    # Имя предмета может быть длинным ("Математика (6 класс - повторение...)"),
    # поэтому ищем по substring — выбираем ключ, который содержится в subject_name.
    subject_keywords_blocklist: dict[str, list[str]] = {
        "математика": ["география", "биология", "история", "литература"],
        "алгебра": ["география", "биология"],
        "геометрия": ["биология", "история"],
        "русский язык": ["литература", "история"],
        "литература": ["русский язык"],
        "биология": ["физика", "химия"],
        "физика": ["биология", "химия"],
        "химия": ["биология", "физика"],
        "география": ["биология", "история"],
        "история": ["география"],
    }
    # Находим первый ключ, который substring-match с subject_name.
    blocklist: list[str] = []
    for key, blocked in subject_keywords_blocklist.items():
        if key in subject_name:
            blocklist = blocked
            break
    if blocklist:
        filtered_blocked: list = []
        for c in chunks:
            meta = getattr(c, "metadata", {}) or {}
            mat_title = (meta.get("material_title") or "").lower()
            if any(bad in mat_title for bad in blocklist):
                logger.warning(
                    "RAG safety net: dropping chunk with wrong subject " "(topic=%s material_title=%r blocklist=%s)",
                    topic_id,
                    mat_title,
                    blocklist,
                )
                continue
            filtered_blocked.append(c)
        chunks = filtered_blocked[:top_k]

    if not chunks:
        return None, []

    # Форматируем chunk'и в читаемый контекст для LLM + собираем sources.
    # app/rag.py::DocumentChunk: id, material_id, text, embedding, metadata.
    # material_title и page_number — в metadata dict.
    lines = [f"Контекст из загруженных учебников (top-{len(chunks)} chunk'ов):"]
    sources: list[dict] = []
    for i, c in enumerate(chunks, 1):
        meta = getattr(c, "metadata", {}) or {}
        mat_title = meta.get("material_title") or f"Материал {getattr(c, 'material_id', '?')}"
        page = meta.get("page_number")
        text = (getattr(c, "text", "") or "").strip()[:800]
        page_str = f", стр. {page}" if page else ""
        lines.append(f"\n[{i}] {mat_title}{page_str}:\n{text}\n")
        # Sprint 4.1.3: собираем source для UI
        sources.append(
            {
                "chunk_id": getattr(c, "id", None),
                "material_id": getattr(c, "material_id", None),
                "material_title": mat_title,
                "page_number": page,
                "part": meta.get("part"),
                "topic_id": meta.get("topic_id"),
                "topic_name": meta.get("topic_name"),
                "snippet": text[:220],
            }
        )
    return "\n".join(lines), _dedupe_rag_sources(sources)
