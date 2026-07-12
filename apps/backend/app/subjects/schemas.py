"""Pydantic-схемы для учебной структуры."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


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
    name: str
    description: str | None
    difficulty: int
    order_index: int


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