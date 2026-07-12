"""Pydantic-схемы для диагностики."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DiagnosticSessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    subject_id: int
    status: str
    total_questions: int
    correct_count: int
    overall_score: float
    weak_topics: str | None
    recommendations: str | None
    started_at: datetime
    finished_at: datetime | None


class DiagnosticQuestionOut(BaseModel):
    session_id: int
    topic_id: int
    topic_name: str
    subject_name: str
    difficulty: int
    question_text: str