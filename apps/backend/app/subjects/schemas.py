"""Pydantic-схемы для учебной структуры.

Sprint 2026-08-22:
- Введены явные readiness evidence-поля (manifest_ready, mapping_ready,
  import_ready, rag_ready, practice_ready, manual_smoke_ready, pilot_visible,
  promotion_allowed). Они независимы и должны выставляться явным pipeline
  шагом, а не вычисляться из counts.
- mvp_status остаётся для обратной совместимости с frontend, но compute
  логика стала fail-closed: только при всех evidence_ready=true
  mvp_status=mvp_ready. Иначе — preview/internal_mvp/blocked_ocr/not_available
  по явной причине.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# Evidence status values, которые могут появляться в mvp_status после fail-closed.
MVP_STATUS_VALUES = (
    "mvp_ready",  # все evidence gates закрыты
    "internal_mvp",  # технически есть, но не для самостоятельного теста
    "preview",  # навигация/обработка, не pilot
    "blocked_ocr",  # OCR/caption/formula QA не закрыта
    "not_available",  # источник или mapping отсутствует
)


class SubjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    description: str | None
    color: str | None
    icon: str | None
    recommended_grade: int
    age_min: int
    age_max: int
    is_active: bool

    # ---- Evidence gates (fail-closed) ----------------------------------
    manifest_ready: bool = False
    mapping_ready: bool = False
    import_ready: bool = False
    rag_ready: bool = False
    practice_ready: bool = False
    manual_smoke_ready: bool = False

    # ---- Promotion gate -------------------------------------------------
    pilot_visible: bool = False
    promotion_allowed: bool = False

    # ---- Computed output (kept for frontend compat) ---------------------
    mvp_status: str = "preview"
    support_note: str = "Preview: учебный маршрут виден, но материалы/RAG ещё не подтверждены."

    # ---- Counts (read-only diagnostics) ---------------------------------
    route_ready: bool = False
    topic_count: int = 0
    route_topic_count: int = 0
    source_topic_count: int = 0
    practice_topic_count: int = 0


class SectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    subject_id: int
    name: str
    description: str | None
    order_index: int


class TopicOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    section_id: int
    # Sprint 3.9.7.3: добавляем subject_id чтобы фронт мог строить
    # back-link на /subjects/{subject_id} (страница со списком тем предмета).
    subject_id: int = 0
    name: str
    description: str | None
    difficulty: int
    order_index: int


class TopicFollowupOut(BaseModel):
    label: str
    prompt: str
    kind: str = "choice"
    order_index: int = 0


class SubtopicOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    topic_id: int
    name: str
    description: str | None
    order_index: int


class MaterialOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    topic_id: int
    title: str
    content: str
    source: str | None
    file_path: str | None
    created_at: datetime


class QuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    topic_id: int
    type: str
    difficulty: int
    question_text: str
    payload: str | None
    correct_answer: str
    explanation: str | None
    typical_mistakes: str | None


class MathTopicPlanOut(BaseModel):
    topic_id: int
    order: int
    section: str
    tier: str
    focus: str
    checkpoint: bool = False
    next_topic_id: int | None = None
