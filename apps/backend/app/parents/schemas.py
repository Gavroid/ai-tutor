"""Схемы для родительского кабинета (Sprint 3)."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class InviteOut(BaseModel):
    code: str
    expires_at: datetime | None = None


class AcceptInviteIn(BaseModel):
    code: str = Field(min_length=4, max_length=32)


class LinkedStudent(BaseModel):
    student_id: int
    display_name: str
    email: str
    linked_at: datetime


class WeakTopic(BaseModel):
    topic_id: int
    topic_name: str
    subject_name: str
    mastery: float
    attempts_count: int


class DailyActivity(BaseModel):
    date: str
    attempts: int


class StudentBrief(BaseModel):
    id: int
    display_name: str
    email: str


class ChildOverview(BaseModel):
    student: StudentBrief
    total_attempts: int
    correct_attempts: int
    accuracy: float
    average_mastery: float
    weak_topics: list[WeakTopic]
    daily_activity: list[DailyActivity]
    privacy_note: str


# === Sprint 3.1: расширенный дашборд ===

class SubjectMastery(BaseModel):
    """Mastery по предмету (агрегат по всем темам)."""

    subject_id: int
    subject_name: str
    topics_total: int
    topics_attempted: int
    avg_mastery: float
    accuracy: float


class TopMistake(BaseModel):
    """Типичная ошибка (агрегат по mistake_type)."""

    mistake_type: str
    description: str
    topic_id: int
    topic_name: str
    count: int
    last_seen: datetime


class StudyStreak(BaseModel):
    """Серия занятий."""

    current_streak_days: int
    longest_streak_days: int
    last_active_date: str | None
    total_active_days: int


class SubjectTimeStats(BaseModel):
    """Время на платформе (по попыткам — proxy)."""

    total_attempts: int
    last_7_days: int
    last_30_days: int
    avg_per_active_day: float


class ChildDashboard(BaseModel):
    """Полный дашборд для родителя (Sprint 3.1)."""

    student: StudentBrief
    generated_at: datetime

    # Общее
    total_attempts: int
    correct_attempts: int
    accuracy: float
    average_mastery: float

    # По предметам
    subject_mastery: list[SubjectMastery]

    # Слабые темы и типичные ошибки
    weak_topics: list[WeakTopic]
    top_mistakes: list[TopMistake]

    # Серии и активность
    streak: StudyStreak
    time_stats: SubjectTimeStats

    # Динамика (последние 30 дней по дням)
    daily_activity_30d: list[DailyActivity]

    # Sprint 3.3
    due_for_review_count: int

    privacy_note: str
