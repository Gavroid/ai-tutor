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
    """Parent-facing student summary.

    Sprint 2026-08-23 (H2.3): ``email`` удалён из parent-facing payload —
    PII minimization. Parent знает ребёнка лично, ему не нужен email
    ребёнка в API-ответе. Если нужен в UI — брать из JWT/auth.
    """

    student_id: int
    display_name: str
    linked_at: datetime


class WeakTopic(BaseModel):
    topic_id: int
    topic_name: str
    subject_name: str
    mastery: float
    attempts_count: int


# Sprint 4.2: схема для review_topics (top-5 по last_reviewed_at).
# Отдельная от WeakTopic — review_topics могут включать темы с mastery >= 60%
# (если они просто давно не повторялись), что не является "слабыми".
class ReviewTopic(BaseModel):
    topic_id: int
    topic_name: str
    subject_name: str
    mastery: float  # 0..1 (consistency с WeakTopic)
    last_reviewed_at: datetime | None  # None = никогда не повторяли


class DailyActivity(BaseModel):
    date: str
    attempts: int


class StudentBrief(BaseModel):
    """Brief student info inside ChildOverview (parent-facing).

    Sprint 2026-08-23 (H2.3): ``email`` удалён — PII minimization.
    """

    id: int
    display_name: str


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


class ParentRecommendation(BaseModel):
    """Actionable recommendation for parent, not raw analytics."""

    title: str
    detail: str
    tone: str = "neutral"
    topic_id: int | None = None
    topic_name: str | None = None


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

    # Stage 5: parent-friendly actionable summary.
    summary: str
    recommendations: list[ParentRecommendation]
    last_activity_label: str

    privacy_note: str


# === Sprint 3.11: parent badges view ===
class ChildBadgeItem(BaseModel):
    """Один бейдж ребёнка для родительского дашборда."""

    slug: str
    title: str
    description: str
    icon: str
    earned_at: datetime
    category: str  # count / effort / streak / context


class ChildBadgeSummary(BaseModel):
    """Сводка по бейджам ребёнка для родителя.

    Sprint 3.11: родительский дашборд показывает все бейджи ребёнка с разбивкой
    по категориям. Read-only — родитель НЕ может influence какие бейджи даются.
    Sprint 3.13: добавлено new_since_last_seen — счётчик "новых с прошлого визита".
    """

    student_id: int
    total_earned: int
    total_available: int
    # Прогресс по категориям: {"count": "5 / 15", "effort": "3 / 11", ...}
    by_category: dict[str, str]
    # Последний полученный бейдж (или null если ещё нет ни одного).
    latest: ChildBadgeItem | None
    # Все earned бейджи (новые первые).
    earned: list[ChildBadgeItem]
    # Slug'и заблокированных бейджей (какие есть в каталоге но не earned).
    locked: list[str]
    # Sprint 3.13: сколько новых бейджей получено с момента последнего просмотра.
    # None если родитель ещё ни разу не открывал дашборд (тогда показываем все).
    new_since_last_seen: int | None
    # Список новых бейджей (title + icon) для краткого превью в баннере.
    new_items: list[ChildBadgeItem]


class MarkBadgesSeenResponse(BaseModel):
    """Ответ на POST /parents/students/{id}/badges/seen."""

    marked_at: datetime
    remaining_new: int  # Сколько ещё осталось (на случай гонки).
