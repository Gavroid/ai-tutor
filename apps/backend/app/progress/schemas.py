"""Pydantic-схемы для прогресса."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AttemptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    topic_id: int
    question_text: str
    user_answer: str
    is_correct: bool
    score: float
    feedback: str | None
    created_at: datetime


class AttemptCreate(BaseModel):
    """Запись попытки вручную (используется после AI-проверки)."""

    topic_id: int
    question_text: str = Field(min_length=1, max_length=4000)
    user_answer: str = Field(min_length=1, max_length=4000)
    correct_answer: str = Field(min_length=1, max_length=4000)
    is_correct: bool
    score: float = Field(ge=0.0, le=1.0)
    feedback: str | None = None


class MistakeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    topic_id: int
    mistake_type: str
    description: str
    count: int
    last_seen: datetime


class ProgressOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    topic_id: int
    mastery_score: float
    attempts_count: int
    correct_count: int
    updated_at: datetime


class TopicProgress(BaseModel):
    topic_id: int
    topic_name: str
    subject_id: int
    subject_name: str
    mastery_score: float
    attempts_count: int
    correct_count: int


# === Sprint 2.2: Spaced Repetition ===
class ReviewItem(BaseModel):
    """Тема, которую нужно повторить сегодня."""

    topic_id: int
    topic_name: str
    subject_name: str
    mastery_score: float
    review_count: int
    next_review_at: datetime
    days_overdue: int  # отрицательное = ещё рано


class ReviewResultIn(BaseModel):
    """Отметка о прохождении повторения — для SM-2 пересчёта."""

    topic_id: int
    quality: int = Field(ge=0, le=5, description="SM-2 quality (0..5)")
    is_correct: bool = True
    hint_used: bool = False