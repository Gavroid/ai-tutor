"""Pydantic-схемы для teacher endpoints (Sprint 1.2-1.3)."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

SourceType = Literal["text", "file", "topic", "pdf"]
MaterialStatus = Literal["draft", "ai_generated", "teacher_approved", "published"]
Difficulty = Literal["easy", "medium", "hard"]


# ============================================================
# Входные данные для генерации
# ============================================================


class GenerateMaterialIn(BaseModel):
    """Вход для POST /teacher/materials/generate."""

    topic_id: int = Field(..., description="ID темы из curriculum 7 класса")
    source_type: SourceType = "text"
    # Один из этих полей должен быть заполнен (валидация — в endpoint):
    text: str | None = Field(None, max_length=20000)
    topic_hint: str | None = Field(None, max_length=500)
    # file_path заполняется автоматически при загрузке файла
    file_path: str | None = None


# ============================================================
# Структура сгенерированного контента (единый шаблон)
# ============================================================


class KeyIdea(BaseModel):
    idea: str
    terms: list[str] = Field(default_factory=list)


class PracticeTask(BaseModel):
    """Одна практическая задача — приоритет №1 для ученика."""

    difficulty: Difficulty
    question_text: str
    reference_solution: str  # Эталонное решение для авто-проверки
    typical_mistakes: list[str] = Field(default_factory=list)
    hint: str | None = None


class TestQuestion(BaseModel):
    """Мини-тест: один вопрос с 4 вариантами."""

    question_text: str
    options: list[str] = Field(..., min_length=2, max_length=6)
    correct_index: int = Field(..., ge=0)
    explanation: str


class Flashcard(BaseModel):
    """Карточка для spaced repetition."""

    question: str
    answer: str


class MaterialContent(BaseModel):
    """Структура сгенерированного материала — единый шаблон темы."""

    # Заголовок и связки
    title: str
    purpose: str  # «Зачем нужна тема»
    connection_to_prior: str | None = None  # Связь с пройденным

    # Основная часть
    key_ideas: list[KeyIdea] = Field(default_factory=list)
    rule_or_formula: str | None = None
    simple_example: str | None = None
    schema_or_table: str | None = None

    # Подводные камни
    misconception: str | None = None  # Типичное заблуждение
    common_mistake: str | None = None  # Частая ошибка

    # Самопроверка (3 вопроса)
    self_check_questions: list[str] = Field(default_factory=list)

    # Практика (приоритет №1) — минимум 5
    practice_tasks: list[PracticeTask] = Field(default_factory=list)

    # Мини-тест (5 вопросов)
    mini_test: list[TestQuestion] = Field(default_factory=list)

    # Карточки для интервального повторения
    flashcards: list[Flashcard] = Field(default_factory=list)

    # Мета от AI — что он не уверен
    ai_uncertainty_notes: list[str] = Field(default_factory=list)


# ============================================================
# Выходные данные
# ============================================================


class MaterialDraftOut(BaseModel):
    """Ответ /teacher/materials/generate — что вернётся учителю для просмотра."""

    id: int
    topic_id: int
    title: str
    content: MaterialContent
    status: MaterialStatus
    source_type: SourceType
    generated_by: int | None
    approved_by: int | None
    published_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


class MaterialListItem(BaseModel):
    """Краткая карточка для списка /teacher/materials."""

    id: int
    topic_id: int
    title: str
    status: MaterialStatus
    source_type: SourceType
    generated_by: int | None
    approved_by: int | None
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime | None = None


class MaterialUpdateIn(BaseModel):
    """PATCH /teacher/materials/{id} — редактирование Учителем."""

    title: str | None = Field(None, max_length=300)
    content: MaterialContent | None = None
