"""Сервис родительского кабинета.

Возможности:
- Привязка ребёнка к родителю через invite_code
- Просмотр общего прогресса ребёнка (по всем предметам)
- Список слабых тем
- Расширенный дашборд (Sprint 3): mastery по предметам, серии, типичные ошибки
- Не показывает личную переписку ребёнка с AI (privacy)
"""
from __future__ import annotations

import secrets
from datetime import date as _date, datetime, timedelta, timezone

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.progress import models as prog_models
from app.subjects import models as subj_models
from app.users import models as user_models
from app.parents import schemas


def create_invite_for_parent(db: Session, parent: user_models.User) -> str:
    """Создаёт/возвращает активный invite-код для привязки ребёнка.

    Код — 8 hex символов, вводится ребёнком в личном кабинете.
    """
    link = db.scalar(
        select(user_models.ParentStudentLink)
        .where(
            user_models.ParentStudentLink.parent_id == parent.id,
            user_models.ParentStudentLink.status == "active",
        )
    )
    if link is not None:
        # Возвращаем существующий код (стабильный для одного родителя)
        return _invite_code(link.id)

    # Создаём новую link (без student_id) — заполнится когда ребёнок примет
    link = user_models.ParentStudentLink(
        parent_id=parent.id,
        student_id=parent.id,  # placeholder, заменим при привязке
        status="pending",
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return _invite_code(link.id)


def _invite_code(link_id: int) -> str:
    return f"P-{link_id:06d}-{secrets.token_hex(3).upper()}"


def accept_invite(db: Session, student: user_models.User, code: str) -> bool:
    """Ребёнок вводит код — привязывается к родителю."""
    # Парсим код формата P-000123-ABC
    parts = code.strip().split("-")
    if len(parts) != 3 or parts[0] != "P":
        raise ValueError("Неверный формат кода")
    try:
        link_id = int(parts[1])
    except ValueError as exc:
        raise ValueError("Неверный формат кода") from exc

    link = db.get(user_models.ParentStudentLink, link_id)
    if link is None or link.status != "pending":
        raise ValueError("Код не найден или уже использован")
    if link.parent_id == student.id:
        raise ValueError("Нельзя привязать себя")

    link.student_id = student.id
    link.status = "active"
    db.commit()
    return True


def list_linked_students(db: Session, parent: user_models.User) -> list[dict]:
    rows = db.execute(
        select(
            user_models.User.id,
            user_models.User.display_name,
            user_models.User.email,
            user_models.ParentStudentLink.created_at,
        )
        .join(
            user_models.ParentStudentLink,
            user_models.ParentStudentLink.student_id == user_models.User.id,
        )
        .where(
            user_models.ParentStudentLink.parent_id == parent.id,
            user_models.ParentStudentLink.status == "active",
        )
    ).all()
    return [
        {
            "student_id": r[0],
            "display_name": r[1],
            "email": r[2],
            "linked_at": r[3],
        }
        for r in rows
    ]


def child_overview(db: Session, parent: user_models.User, student_id: int) -> dict | None:
    """Общий отчёт по ребёнку: только сводка, без личной переписки."""
    # Проверяем, что student привязан к parent
    link = db.scalar(
        select(user_models.ParentStudentLink).where(
            user_models.ParentStudentLink.parent_id == parent.id,
            user_models.ParentStudentLink.student_id == student_id,
            user_models.ParentStudentLink.status == "active",
        )
    )
    if link is None:
        return None

    student = db.get(user_models.User, student_id)
    if student is None:
        return None

    # Общая статистика по попыткам
    total_attempts = db.scalar(
        select(func.count(prog_models.Attempt.id)).where(
            prog_models.Attempt.user_id == student_id
        )
    ) or 0

    correct_attempts = db.scalar(
        select(func.count(prog_models.Attempt.id)).where(
            prog_models.Attempt.user_id == student_id,
            prog_models.Attempt.is_correct.is_(True),
        )
    ) or 0

    # Средний mastery по всем темам
    avg_mastery = db.scalar(
        select(func.avg(prog_models.Progress.mastery_score)).where(
            prog_models.Progress.user_id == student_id
        )
    ) or 0.0

    # Слабые темы (mastery < 0.6)
    weak = db.execute(
        select(
            subj_models.Topic.id,
            subj_models.Topic.name,
            subj_models.Subject.name,
            prog_models.Progress.mastery_score,
            prog_models.Progress.attempts_count,
        )
        .join(prog_models.Progress, prog_models.Progress.topic_id == subj_models.Topic.id)
        .join(subj_models.Section, subj_models.Topic.section_id == subj_models.Section.id)
        .join(subj_models.Subject, subj_models.Section.subject_id == subj_models.Subject.id)
        .where(prog_models.Progress.user_id == student_id)
        .where(prog_models.Progress.mastery_score < 0.6)
        .order_by(prog_models.Progress.mastery_score.asc())
        .limit(10)
    ).all()

    # Активность по дням (последние 7 дней)
    since = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    since = since.replace(day=max(1, since.day - 6))  # последние 7 дней
    daily = db.execute(
        select(
            func.date(prog_models.Attempt.created_at).label("day"),
            func.count(prog_models.Attempt.id).label("count"),
        )
        .where(
            prog_models.Attempt.user_id == student_id,
            prog_models.Attempt.created_at >= since,
        )
        .group_by(func.date(prog_models.Attempt.created_at))
        .order_by(func.date(prog_models.Attempt.created_at))
    ).all()

    return {
        "student": {
            "id": student.id,
            "display_name": student.display_name,
            "email": student.email,
        },
        "total_attempts": int(total_attempts),
        "correct_attempts": int(correct_attempts),
        "accuracy": float(correct_attempts) / total_attempts if total_attempts > 0 else 0.0,
        "average_mastery": round(float(avg_mastery), 3),
        "weak_topics": [
            {
                "topic_id": r[0],
                "topic_name": r[1],
                "subject_name": r[2],
                "mastery": round(float(r[3]), 3),
                "attempts_count": int(r[4]),
            }
            for r in weak
        ],
        "daily_activity": [
            {"date": str(r[0]), "attempts": int(r[1])} for r in daily
        ],
        "privacy_note": "Переписка с AI-репетитором недоступна родителю по соображениям приватности.",
    }


# === Sprint 3.1: расширенный дашборд родителя ===

def _ensure_parent_of(db: Session, parent: user_models.User, student_id: int) -> bool:
    """True если student привязан к parent (active link)."""
    link = db.scalar(
        select(user_models.ParentStudentLink).where(
            user_models.ParentStudentLink.parent_id == parent.id,
            user_models.ParentStudentLink.student_id == student_id,
            user_models.ParentStudentLink.status == "active",
        )
    )
    return link is not None


def _compute_streak(active_dates: set[str], today_str: str) -> tuple[int, int, int]:
    """Считает current_streak (с today назад) и longest_streak."""
    if not active_dates:
        return 0, 0, 0

    # longest streak: идём по отсортированным датам
    sorted_dates = sorted(active_dates)
    longest = 1
    cur_run = 1
    for i in range(1, len(sorted_dates)):
        d_prev = sorted_dates[i - 1]
        d_cur = sorted_dates[i]
        prev = _date.fromisoformat(d_prev)
        cur = _date.fromisoformat(d_cur)
        if (cur - prev).days == 1:
            cur_run += 1
            longest = max(longest, cur_run)
        else:
            cur_run = 1

    # current streak — от today назад, пока дни идут подряд
    today = _date.fromisoformat(today_str)
    current = 0
    d = today
    while d.isoformat() in active_dates:
        current += 1
        d = d - timedelta(days=1)
    # Если сегодня не было активности — current streak = 0
    # (это мотивирует не пропускать сегодня)
    return current, longest, len(active_dates)


def child_dashboard(
    db: Session,
    parent: user_models.User,
    student_id: int,
) -> schemas.ChildDashboard | None:
    """Расширенный дашборд родителя — все метрики в одном объекте.

    Возвращает None если student не привязан к parent.
    """
    if not _ensure_parent_of(db, parent, student_id):
        return None

    student = db.get(user_models.User, student_id)
    if student is None:
        return None

    today = _date.today()
    today_str = today.isoformat()
    last_30 = today - timedelta(days=30)

    # === Общее ===
    total_attempts = db.scalar(
        select(func.count(prog_models.Attempt.id)).where(
            prog_models.Attempt.user_id == student_id
        )
    ) or 0
    correct_attempts = db.scalar(
        select(func.count(prog_models.Attempt.id)).where(
            prog_models.Attempt.user_id == student_id,
            prog_models.Attempt.is_correct.is_(True),
        )
    ) or 0
    avg_mastery = db.scalar(
        select(func.avg(prog_models.Progress.mastery_score)).where(
            prog_models.Progress.user_id == student_id
        )
    ) or 0.0
    accuracy = float(correct_attempts) / total_attempts if total_attempts > 0 else 0.0

    # === Mastery по предметам ===
    subject_rows = db.execute(
        select(
            subj_models.Subject.id,
            subj_models.Subject.name,
            func.count(func.distinct(subj_models.Topic.id)).label("topics_total"),
            func.count(func.distinct(prog_models.Progress.topic_id)).label(
                "topics_attempted"
            ),
            func.coalesce(func.avg(prog_models.Progress.mastery_score), 0.0).label(
                "avg_mastery"
            ),
        )
        .select_from(subj_models.Subject)
        .join(subj_models.Section, subj_models.Section.subject_id == subj_models.Subject.id)
        .join(
            subj_models.Topic,
            subj_models.Topic.section_id == subj_models.Section.id,
        )
        .outerjoin(
            prog_models.Progress,
            (prog_models.Progress.topic_id == subj_models.Topic.id)
            & (prog_models.Progress.user_id == student_id),
        )
        .where(subj_models.Subject.is_active.is_(True))
        .group_by(subj_models.Subject.id, subj_models.Subject.name)
        .order_by(subj_models.Subject.name)
    ).all()

    # accuracy по предмету — отдельный запрос
    subject_accuracy = {}
    acc_rows = db.execute(
        select(
            subj_models.Subject.id,
            func.count(prog_models.Attempt.id).label("total"),
            func.sum(
                case((prog_models.Attempt.is_correct.is_(True), 1), else_=0)
            ).label("correct"),
        )
        .select_from(subj_models.Subject)
        .join(subj_models.Section, subj_models.Section.subject_id == subj_models.Subject.id)
        .join(
            subj_models.Topic,
            subj_models.Topic.section_id == subj_models.Section.id,
        )
        .join(
            prog_models.Attempt,
            prog_models.Attempt.topic_id == subj_models.Topic.id,
        )
        .where(prog_models.Attempt.user_id == student_id)
        .group_by(subj_models.Subject.id)
    ).all()
    for r in acc_rows:
        total = int(r[1] or 0)
        correct = int(r[2] or 0)
        subject_accuracy[r[0]] = float(correct) / total if total > 0 else 0.0

    subject_mastery = [
        schemas.SubjectMastery(
            subject_id=r[0],
            subject_name=r[1],
            topics_total=int(r[2] or 0),
            topics_attempted=int(r[3] or 0),
            avg_mastery=round(float(r[4]), 3),
            accuracy=round(subject_accuracy.get(r[0], 0.0), 3),
        )
        for r in subject_rows
    ]

    # === Слабые темы ===
    weak_rows = db.execute(
        select(
            subj_models.Topic.id,
            subj_models.Topic.name,
            subj_models.Subject.name,
            prog_models.Progress.mastery_score,
            prog_models.Progress.attempts_count,
        )
        .join(prog_models.Progress, prog_models.Progress.topic_id == subj_models.Topic.id)
        .join(subj_models.Section, subj_models.Topic.section_id == subj_models.Section.id)
        .join(subj_models.Subject, subj_models.Section.subject_id == subj_models.Subject.id)
        .where(prog_models.Progress.user_id == student_id)
        .where(prog_models.Progress.mastery_score < 0.6)
        .order_by(prog_models.Progress.mastery_score.asc())
        .limit(10)
    ).all()

    weak_topics = [
        schemas.WeakTopic(
            topic_id=r[0],
            topic_name=r[1],
            subject_name=r[2],
            mastery=round(float(r[3]), 3),
            attempts_count=int(r[4]),
        )
        for r in weak_rows
    ]

    # === Топ типичных ошибок ===
    mistake_rows = db.execute(
        select(
            prog_models.Mistake.mistake_type,
            prog_models.Mistake.description,
            prog_models.Mistake.topic_id,
            subj_models.Topic.name,
            prog_models.Mistake.count,
            prog_models.Mistake.last_seen,
        )
        .join(subj_models.Topic, subj_models.Topic.id == prog_models.Mistake.topic_id)
        .where(prog_models.Mistake.user_id == student_id)
        .order_by(prog_models.Mistake.count.desc())
        .limit(10)
    ).all()
    top_mistakes = [
        schemas.TopMistake(
            mistake_type=r[0],
            description=r[1],
            topic_id=r[2],
            topic_name=r[3],
            count=int(r[4]),
            last_seen=r[5],
        )
        for r in mistake_rows
    ]

    # === Активность (для streak и time_stats) ===
    activity_rows = db.execute(
        select(
            func.date(prog_models.Attempt.created_at).label("day"),
            func.count(prog_models.Attempt.id).label("count"),
        )
        .where(prog_models.Attempt.user_id == student_id)
        .group_by(func.date(prog_models.Attempt.created_at))
    ).all()

    active_dates = {str(r[0]) for r in activity_rows}
    current_streak, longest_streak, total_active_days = _compute_streak(
        active_dates, today_str
    )

    last_7 = sum(int(r[1]) for r in activity_rows if str(r[0]) >= (today - timedelta(days=7)).isoformat())
    last_30_count = sum(int(r[1]) for r in activity_rows if str(r[0]) >= last_30.isoformat())

    # daily activity за 30 дней (с заполнением пропусков нулями)
    daily_map = {str(r[0]): int(r[1]) for r in activity_rows}
    daily_30: list[schemas.DailyActivity] = []
    for i in range(30):
        d = today - timedelta(days=i)
        d_str = d.isoformat()
        daily_30.append(
            schemas.DailyActivity(
                date=d_str,
                attempts=daily_map.get(d_str, 0),
            )
        )
    daily_30.reverse()  # от старых к новым

    # === Due for review ===
    due_count = db.scalar(
        select(func.count(prog_models.Progress.id)).where(
            prog_models.Progress.user_id == student_id,
            prog_models.Progress.next_review_at.is_not(None),
            prog_models.Progress.next_review_at <= datetime.now(timezone.utc),
        )
    ) or 0

    return schemas.ChildDashboard(
        student=schemas.StudentBrief(
            id=student.id,
            display_name=student.display_name,
            email=student.email,
        ),
        generated_at=datetime.now(timezone.utc),
        total_attempts=int(total_attempts),
        correct_attempts=int(correct_attempts),
        accuracy=round(accuracy, 3),
        average_mastery=round(float(avg_mastery), 3),
        subject_mastery=subject_mastery,
        weak_topics=weak_topics,
        top_mistakes=top_mistakes,
        streak=schemas.StudyStreak(
            current_streak_days=current_streak,
            longest_streak_days=longest_streak,
            last_active_date=max(active_dates) if active_dates else None,
            total_active_days=total_active_days,
        ),
        time_stats=schemas.SubjectTimeStats(
            total_attempts=int(total_attempts),
            last_7_days=last_7,
            last_30_days=last_30_count,
            avg_per_active_day=round(
                float(total_attempts) / max(total_active_days, 1), 2
            ),
        ),
        daily_activity_30d=daily_30,
        due_for_review_count=int(due_count),
        privacy_note=(
            "Родитель видит агрегированные метрики. Содержимое чатов ребёнка "
            "с AI-репетитором не отображается (приватность)."
        ),
    )