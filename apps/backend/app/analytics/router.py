"""Learning Analytics V1 for teacher/admin surfaces."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.common.deps import User, require_teacher_or_admin
from app.db.session import get_db
from app.progress import models as progress_models
from app.subjects import models as subject_models

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


class AnalyticsTotals(BaseModel):
    attempts: int
    correct: int
    accuracy: float
    active_topics: int
    weak_topics: int
    average_mastery: float


class SubjectAnalytics(BaseModel):
    subject_id: int
    subject_code: str
    subject_name: str
    attempts: int
    correct: int
    accuracy: float
    average_mastery: float
    active_topics: int
    weak_topics: int


class WeakTopicAnalytics(BaseModel):
    topic_id: int
    topic_name: str
    subject_id: int
    subject_code: str
    subject_name: str
    mastery_score: float
    attempts_count: int
    correct_count: int


class ActivityAnalytics(BaseModel):
    date: str
    attempts: int
    correct: int


class LearningAnalyticsOut(BaseModel):
    totals: AnalyticsTotals
    subjects: list[SubjectAnalytics]
    weak_topics: list[WeakTopicAnalytics]
    recent_activity: list[ActivityAnalytics]


def _ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 4)


@router.get("/learning", response_model=LearningAnalyticsOut)
def learning_analytics(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current: User = Depends(require_teacher_or_admin()),
):
    """Aggregate learning outcomes for teacher/admin.

    Returns only aggregate learning data: attempts, accuracy, mastery, weak topics,
    and recent activity. It does not expose raw AI chat content.
    """
    del current
    progress_rows = db.execute(
        select(
            progress_models.Progress,
            subject_models.Topic,
            subject_models.Section,
            subject_models.Subject,
        )
        .join(subject_models.Topic, subject_models.Topic.id == progress_models.Progress.topic_id)
        .join(subject_models.Section, subject_models.Section.id == subject_models.Topic.section_id)
        .join(subject_models.Subject, subject_models.Subject.id == subject_models.Section.subject_id)
        .order_by(subject_models.Subject.id, subject_models.Topic.id)
    ).all()

    total_attempts = sum(int(progress.attempts_count) for progress, *_ in progress_rows)
    total_correct = sum(int(progress.correct_count) for progress, *_ in progress_rows)
    active_topics = sum(1 for progress, *_ in progress_rows if int(progress.attempts_count) > 0)
    weak_topic_rows = [row for row in progress_rows if int(row[0].attempts_count) > 0 and float(row[0].mastery_score) < 0.5]
    average_mastery = round(
        sum(float(progress.mastery_score) for progress, *_ in progress_rows) / len(progress_rows),
        4,
    ) if progress_rows else 0.0

    subject_map: dict[int, dict[str, object]] = {}
    for progress, _topic, _section, subject in progress_rows:
        item = subject_map.setdefault(
            subject.id,
            {
                "subject_id": subject.id,
                "subject_code": subject.code,
                "subject_name": subject.name,
                "attempts": 0,
                "correct": 0,
                "mastery_sum": 0.0,
                "active_topics": 0,
                "weak_topics": 0,
            },
        )
        item["attempts"] = int(item["attempts"]) + int(progress.attempts_count)
        item["correct"] = int(item["correct"]) + int(progress.correct_count)
        item["mastery_sum"] = float(item["mastery_sum"]) + float(progress.mastery_score)
        if int(progress.attempts_count) > 0:
            item["active_topics"] = int(item["active_topics"]) + 1
        if int(progress.attempts_count) > 0 and float(progress.mastery_score) < 0.5:
            item["weak_topics"] = int(item["weak_topics"]) + 1

    subjects = [
        SubjectAnalytics(
            subject_id=int(item["subject_id"]),
            subject_code=str(item["subject_code"]),
            subject_name=str(item["subject_name"]),
            attempts=int(item["attempts"]),
            correct=int(item["correct"]),
            accuracy=_ratio(int(item["correct"]), int(item["attempts"])),
            average_mastery=round(float(item["mastery_sum"]) / max(int(item["active_topics"]), 1), 4),
            active_topics=int(item["active_topics"]),
            weak_topics=int(item["weak_topics"]),
        )
        for item in sorted(subject_map.values(), key=lambda row: (-int(row["weak_topics"]), str(row["subject_name"])))
    ]

    weak_topics = [
        WeakTopicAnalytics(
            topic_id=topic.id,
            topic_name=topic.name,
            subject_id=subject.id,
            subject_code=subject.code,
            subject_name=subject.name,
            mastery_score=round(float(progress.mastery_score), 4),
            attempts_count=int(progress.attempts_count),
            correct_count=int(progress.correct_count),
        )
        for progress, topic, _section, subject in sorted(
            weak_topic_rows,
            key=lambda row: (float(row[0].mastery_score), -int(row[0].attempts_count), int(row[1].id)),
        )[:10]
    ]

    # Use Progress.updated_at here: it is the stable per-topic learning aggregate
    # available across old and new data. Raw attempts can be missing for seeded or
    # migrated progress rows, but Progress still carries attempts/correct counts.
    activity_rows = db.execute(
        select(
            func.date(progress_models.Progress.updated_at).label("day"),
            func.sum(progress_models.Progress.attempts_count),
            func.sum(progress_models.Progress.correct_count),
        )
        .where(progress_models.Progress.attempts_count > 0)
        .group_by(func.date(progress_models.Progress.updated_at))
        .order_by(func.date(progress_models.Progress.updated_at).desc())
        .limit(days)
    ).all()
    recent_activity = [
        ActivityAnalytics(
            date=str(day),
            attempts=int(attempts or 0),
            correct=int(correct or 0),
        )
        for day, attempts, correct in reversed(activity_rows)
    ]

    return LearningAnalyticsOut(
        totals=AnalyticsTotals(
            attempts=total_attempts,
            correct=total_correct,
            accuracy=_ratio(total_correct, total_attempts),
            active_topics=active_topics,
            weak_topics=len(weak_topic_rows),
            average_mastery=average_mastery,
        ),
        subjects=subjects,
        weak_topics=weak_topics,
        recent_activity=recent_activity,
    )
