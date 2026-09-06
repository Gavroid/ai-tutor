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
from datetime import UTC, datetime, timedelta, timezone
from datetime import date as _date

from app.parents import schemas
from app.progress import models as prog_models
from app.student import badges as student_badges  # Sprint 3.11
from app.subjects import models as subj_models
from app.users import models as user_models
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

# Sprint 4.2: mastery thresholds для parent recommendations.
# Решение владельца (audit 2026-09-05, зафиксировано в
# audit-2026-09/13-session-2026-09-04-blocked-decisions.md):
#
#   weak_topics:    mastery < 0.60 (60%)
#   review_topics:  top-5 тем с наиболее старым last_reviewed_at
#
# Эти константы НЕ пересекаются с существующими WEAK_THRESHOLD (0.5) /
# MASTERED_THRESHOLD (0.8) в app/progress/router.py — те используются
# для student-facing dashboard, эти — для parent recommendations.
#
# Sprint 4.1 (single-source) будет читать эти же константы — единая точка
# истины для frontend/backend контракта.
WEAK_MASTERY_THRESHOLD = 0.60  # mastery < 60% → слабая тема
REVIEW_TOPICS_LIMIT = 5  # top-5 тем по last_reviewed_at

# Sprint 3.11: маппинг slug → category для родительского дашборда.
# Должно совпадать с BADGE_CATEGORIES в apps/frontend/app/student/badges/client.tsx.
_BADGE_CATEGORY: dict[str, str] = {
    # count — количество решённых задач.
    "first_step": "count",
    "five_solved": "count",
    "ten_solved": "count",
    "fifty_solved": "count",
    "hundred_solved": "count",
    "two_hundred_solved": "count",
    "three_hundred_solved": "count",
    "four_hundred_solved": "count",
    "five_hundred_solved": "count",
    "six_hundred_solved": "count",
    "seven_hundred_solved": "count",
    "eight_hundred_solved": "count",
    "nine_hundred_solved": "count",
    "thousand_solved": "count",
    "fifteen_hundred_solved": "count",
    # effort — усилие и качество.
    "explained_in_own_words": "effort",
    "five_quality_correct": "effort",
    "twenty_quality_correct": "effort",
    "fifty_quality_correct": "effort",
    "returned_to_hard": "effort",
    "mastered_topic": "effort",
    "mastered_five_topics": "effort",
    "all_basics": "effort",
    "review_count_10": "effort",
    "review_count_50": "effort",
    "asked_question": "effort",
    "correct_count_25": "effort",
    "correct_count_75": "effort",
    "correct_count_150": "effort",
    "correct_count_500": "effort",
    # streak — серии.
    "streak_3": "streak",
    "streak_7": "streak",
    "streak_14": "streak",
    "streak_30": "streak",
    "streak_45": "streak",
    "streak_60": "streak",
    "streak_100": "streak",
    "streak_180": "streak",
    "streak_365": "streak",
    "returned_after_pause": "streak",
    "streak_correct_5": "streak",
    "streak_correct_14": "streak",
    "streak_correct_30": "streak",
    "returned_twice": "streak",
    "returned_five": "streak",
    # context — контекст и время.
    "polymath_week": "context",
    "early_bird": "context",
    "night_owl": "context",
    "weekend_warrior": "context",
    "perfect_five": "context",
    "ten_in_a_row": "context",
    "twenty_in_a_row": "context",
    "fifty_in_a_row": "context",
    "morning_streak_5": "context",
    "lunch_learner": "context",
    "lunch_master": "context",
    "late_night_hero": "context",
    "weekend_regular_2": "context",
    "weekend_master_8": "context",
    "morning_streak_14": "context",
}


def create_invite_for_parent(db: Session, parent: user_models.User) -> str:
    """Создаёт/возвращает активный invite-код для привязки ребёнка.

    Код — 8 hex символов, вводится ребёнком в личном кабинете.
    """
    link = db.scalar(
        select(user_models.ParentStudentLink)
        .where(
            user_models.ParentStudentLink.parent_id == parent.id,
            user_models.ParentStudentLink.status == "pending",
            user_models.ParentStudentLink.student_id == parent.id,
        )
        .order_by(user_models.ParentStudentLink.id.desc())
    )
    if link is not None:
        # Возвращаем существующий pending-код, пока ребёнок его не принял.
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
            user_models.ParentStudentLink.student_id != parent.id,
            user_models.User.role == user_models.Role.STUDENT,
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
    total_attempts = (
        db.scalar(select(func.count(prog_models.Attempt.id)).where(prog_models.Attempt.user_id == student_id)) or 0
    )

    correct_attempts = (
        db.scalar(
            select(func.count(prog_models.Attempt.id)).where(
                prog_models.Attempt.user_id == student_id,
                prog_models.Attempt.is_correct.is_(True),
            )
        )
        or 0
    )

    # Средний mastery по всем темам
    avg_mastery = (
        db.scalar(
            select(func.avg(prog_models.Progress.mastery_score)).where(prog_models.Progress.user_id == student_id)
        )
        or 0.0
    )

    # Слабые темы (Sprint 4.2: mastery < WEAK_MASTERY_THRESHOLD = 0.60 = 60%)
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
        .where(prog_models.Progress.mastery_score < WEAK_MASTERY_THRESHOLD)
        .order_by(prog_models.Progress.mastery_score.asc())
        .limit(10)
    ).all()

    # Активность по дням (последние 7 дней)
    since = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
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
            # Sprint 2026-08-23 (H2.3): email удалён — PII minimization.
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
        "daily_activity": [{"date": str(r[0]), "attempts": int(r[1])} for r in daily],
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


def _parent_summary(
    total_attempts: int,
    accuracy: float,
    weak_topics: list[schemas.WeakTopic],
    due_count: int,
    last_activity_label: str,
) -> str:
    if total_attempts == 0:
        return "Пока нет учебных попыток. Лучше начать с одной короткой темы и 2–3 задач."
    if weak_topics:
        return f"Есть темы для повторения: начните с «{weak_topics[0].topic_name}». Последняя активность: {last_activity_label}."
    if due_count > 0:
        return f"Есть {due_count} тем к повторению. Лучше закрепить их до новых тем."
    if accuracy >= 0.8:
        return f"Темп хороший: точность около {round(accuracy * 100)}%. Можно дать чуть более сложную практику."
    return f"Точность около {round(accuracy * 100)}%. Лучше закрепить текущие темы короткой практикой."


def _parent_recommendations(
    weak_topics: list[schemas.WeakTopic],
    due_count: int,
    accuracy: float,
    last_7: int,
) -> list[schemas.ParentRecommendation]:
    recs: list[schemas.ParentRecommendation] = []
    if weak_topics:
        # Sprint 3.19 (audit D1): до 5 weak-topic рекомендаций — как у ученика
        # в /subjects и как в /parents (9b1e0f4). Раньше была только
        # weak_topics[0] → «1 у родителя, 5 у ученика» на /parent/dashboard/[id].
        for topic in weak_topics[:5]:
            recs.append(
                schemas.ParentRecommendation(
                    title="Повторить слабую тему",
                    detail=f"Начните с темы «{topic.topic_name}»: mastery {round(topic.mastery * 100)}%, попыток {topic.attempts_count}.",
                    tone="warning",
                    topic_id=topic.topic_id,
                    topic_name=topic.topic_name,
                )
            )
    if due_count > 0:
        recs.append(
            schemas.ParentRecommendation(
                title="Сделать повторение",
                detail=f"К повторению сейчас {due_count} тем. Лучше 10 минут повторения, чем новая сложная тема.",
                tone="info",
            )
        )
    if last_7 == 0:
        recs.append(
            schemas.ParentRecommendation(
                title="Вернуться мягко",
                detail="За последние 7 дней нет попыток. Начните с лёгкой темы и одной задачи без давления.",
                tone="neutral",
            )
        )
    elif accuracy < 0.6:
        recs.append(
            schemas.ParentRecommendation(
                title="Снизить сложность",
                detail="Точность ниже 60%. Лучше разобрать пример и дать похожую простую задачу.",
                tone="warning",
            )
        )
    if not recs:
        recs.append(
            schemas.ParentRecommendation(
                title="Продолжать план",
                detail="Критичных слабых сигналов нет. Можно продолжать следующую P0/P1 тему.",
                tone="success",
            )
        )
    # Sprint 3.19: cap 3 → 5 (как у ученика; weak-рекомендации идут первыми).
    return recs[:5]


def get_review_topics(db: Session, student_id: int) -> list[schemas.ReviewTopic]:
    """Sprint 4.2: top-N (REVIEW_TOPICS_LIMIT=5) тем по last_reviewed_at.

    Решение владельца (Sprint 4.2=A):
    - "К повторению" — top-5 тем с наиболее старым last_reviewed_at.
    - NULL трактуется как "никогда не повторяли" → попадают первыми.
    - Сортировка детерминированная: NULLs first, затем ASC, tie-breaker по topic_id.
    - Пересечение с weak_topics РАЗРЕШЕНО (semantically correct).

    Sprint 4.1 (single-source) будет использовать эту функцию для
    /api/v1/parents/students/{id}/recommendations endpoint.
    """
    # Детерминированная сортировка через CASE:
    #   last_reviewed_at IS NULL → 0 (идут первыми)
    #   last_reviewed_at NOT NULL → 1
    # затем ASC по дате, tie-breaker по topic_id.
    nulls_first = case(
        (prog_models.Progress.last_reviewed_at.is_(None), 0),
        else_=1,
    )
    rows = db.execute(
        select(
            subj_models.Topic.id,
            subj_models.Topic.name,
            subj_models.Subject.name,
            prog_models.Progress.mastery_score,
            prog_models.Progress.last_reviewed_at,
        )
        .join(prog_models.Progress, prog_models.Progress.topic_id == subj_models.Topic.id)
        .join(subj_models.Section, subj_models.Topic.section_id == subj_models.Section.id)
        .join(subj_models.Subject, subj_models.Section.subject_id == subj_models.Subject.id)
        .where(prog_models.Progress.user_id == student_id)
        # Исключаем только что "пройденные" темы (mastery >= WEAK_MASTERY_THRESHOLD уже фильтруется в weak_topics;
        # для review включаем ВСЕ темы с Progress — даже mastery=100%, если давно не повторяли).
        .order_by(
            nulls_first,
            prog_models.Progress.last_reviewed_at.asc().nulls_first(),
            subj_models.Topic.id.asc(),  # tie-breaker для детерминизма
        )
        .limit(REVIEW_TOPICS_LIMIT)
    ).all()

    return [
        schemas.ReviewTopic(
            topic_id=r[0],
            topic_name=r[1],
            subject_name=r[2],
            mastery=r[3] or 0.0,
            last_reviewed_at=r[4],
        )
        for r in rows
    ]


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
    total_attempts = (
        db.scalar(select(func.count(prog_models.Attempt.id)).where(prog_models.Attempt.user_id == student_id)) or 0
    )
    correct_attempts = (
        db.scalar(
            select(func.count(prog_models.Attempt.id)).where(
                prog_models.Attempt.user_id == student_id,
                prog_models.Attempt.is_correct.is_(True),
            )
        )
        or 0
    )
    avg_mastery = (
        db.scalar(
            select(func.avg(prog_models.Progress.mastery_score)).where(prog_models.Progress.user_id == student_id)
        )
        or 0.0
    )
    accuracy = float(correct_attempts) / total_attempts if total_attempts > 0 else 0.0

    # === Mastery по предметам ===
    subject_rows = db.execute(
        select(
            subj_models.Subject.id,
            subj_models.Subject.name,
            func.count(func.distinct(subj_models.Topic.id)).label("topics_total"),
            func.count(func.distinct(prog_models.Progress.topic_id)).label("topics_attempted"),
            func.coalesce(func.avg(prog_models.Progress.mastery_score), 0.0).label("avg_mastery"),
        )
        .select_from(subj_models.Subject)
        .join(subj_models.Section, subj_models.Section.subject_id == subj_models.Subject.id)
        .join(
            subj_models.Topic,
            subj_models.Topic.section_id == subj_models.Section.id,
        )
        .outerjoin(
            prog_models.Progress,
            (prog_models.Progress.topic_id == subj_models.Topic.id) & (prog_models.Progress.user_id == student_id),
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
            func.sum(case((prog_models.Attempt.is_correct.is_(True), 1), else_=0)).label("correct"),
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
    current_streak, longest_streak, total_active_days = _compute_streak(active_dates, today_str)

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
    due_count = (
        db.scalar(
            select(func.count(prog_models.Progress.id)).where(
                prog_models.Progress.user_id == student_id,
                prog_models.Progress.next_review_at.is_not(None),
                prog_models.Progress.next_review_at <= datetime.now(UTC),
            )
        )
        or 0
    )

    last_activity_label = max(active_dates) if active_dates else "активности пока нет"
    summary = _parent_summary(
        int(total_attempts),
        accuracy,
        weak_topics,
        int(due_count),
        last_activity_label,
    )
    recommendations = _parent_recommendations(
        weak_topics,
        int(due_count),
        accuracy,
        last_7,
    )

    return schemas.ChildDashboard(
        student=schemas.StudentBrief(
            id=student.id,
            display_name=student.display_name,
            # Sprint 2026-08-23 (H2.3): email удалён — PII minimization.
        ),
        generated_at=datetime.now(UTC),
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
            avg_per_active_day=round(float(total_attempts) / max(total_active_days, 1), 2),
        ),
        daily_activity_30d=daily_30,
        due_for_review_count=int(due_count),
        summary=summary,
        recommendations=recommendations,
        last_activity_label=last_activity_label,
        privacy_note=(
            "Родитель видит агрегированные метрики. Содержимое чатов ребёнка "
            "с AI-репетитором не отображается (приватность)."
        ),
    )


# === Sprint 3.11: parent badges view ===
def child_badges_summary(db: Session, parent: user_models.User, student_id: int) -> schemas.ChildBadgeSummary | None:
    """Получить сводку по бейджам ребёнка для родительского дашборда.

    Returns:
        ChildBadgeSummary или None если ребёнок не привязан к этому родителю.
    """
    if not _ensure_parent_of(db, parent, student_id):
        return None

    from app.student.models import BadgeDefinition, UserBadge

    # 1. Каталог (slug → title, description, icon).
    defs = db.execute(select(BadgeDefinition)).scalars().all()
    catalog: dict[str, BadgeDefinition] = {d.slug: d for d in defs}
    total_available = len(defs)

    # 2. Все earned бейджи ребёнка (newest first).
    earned_rows = (
        db.execute(select(UserBadge).where(UserBadge.user_id == student_id).order_by(UserBadge.awarded_at.desc()))
        .scalars()
        .all()
    )

    earned_items: list[schemas.ChildBadgeItem] = []
    earned_slugs: set[str] = set()
    for ub in earned_rows:
        d = catalog.get(ub.badge_slug)
        if d is None:
            continue
        earned_items.append(
            schemas.ChildBadgeItem(
                slug=ub.badge_slug,
                title=d.title,
                description=d.description,
                icon=d.icon,
                earned_at=ub.awarded_at,
                category=_BADGE_CATEGORY.get(ub.badge_slug, "context"),
            )
        )
        earned_slugs.add(ub.badge_slug)

    # 3. Прогресс по категориям.
    # Считаем размер каждой категории по каталогу.
    cat_total: dict[str, int] = {"count": 0, "effort": 0, "streak": 0, "context": 0}
    cat_earned: dict[str, int] = {"count": 0, "effort": 0, "streak": 0, "context": 0}
    for slug in catalog:
        cat = _BADGE_CATEGORY.get(slug, "context")
        cat_total[cat] = cat_total.get(cat, 0) + 1
        if slug in earned_slugs:
            cat_earned[cat] = cat_earned.get(cat, 0) + 1
    by_category: dict[str, str] = {
        cat: f"{cat_earned[cat]} / {cat_total[cat]}" for cat in ("count", "effort", "streak", "context")
    }

    # 4. Locked — slug'и которые есть в каталоге но не earned.
    locked = [slug for slug in catalog if slug not in earned_slugs]

    # 5. Latest — самый свежий earned (или None).
    latest = earned_items[0] if earned_items else None

    # Sprint 3.13: считаем "новые с прошлого визита".
    link = db.execute(
        select(user_models.ParentStudentLink).where(
            user_models.ParentStudentLink.parent_id == parent.id,
            user_models.ParentStudentLink.student_id == student_id,
        )
    ).scalar_one_or_none()

    new_since_last_seen: int | None = None
    new_items: list[schemas.ChildBadgeItem] = []
    if link is not None and link.last_seen_badges_at is not None:
        seen_at = link.last_seen_badges_at
        # Считаем бейджи полученные позже seen_at.
        new_items = [it for it in earned_items if it.earned_at and it.earned_at > seen_at]
        new_since_last_seen = len(new_items)
    elif link is not None:
        # Первый визит — все earned считаются "новыми" но это шумно.
        # Возвращаем None чтобы UI не показывал баннер "X новых" (показать сразу).
        new_since_last_seen = None

    return schemas.ChildBadgeSummary(
        student_id=student_id,
        total_earned=len(earned_items),
        total_available=total_available,
        by_category=by_category,
        latest=latest,
        earned=earned_items,
        locked=locked,
        new_since_last_seen=new_since_last_seen,
        new_items=new_items,
    )


# === Sprint 3.13: parent — mark badges as seen ===
def mark_badges_seen(db: Session, parent: user_models.User, student_id: int) -> tuple[datetime, int] | None:
    """Отметить бейджи ребёнка как просмотренные родителем.

    Returns:
        (marked_at, remaining_new) или None если ребёнок не привязан.
    """
    link = db.execute(
        select(user_models.ParentStudentLink).where(
            user_models.ParentStudentLink.parent_id == parent.id,
            user_models.ParentStudentLink.student_id == student_id,
        )
    ).scalar_one_or_none()
    if link is None:
        return None

    now = datetime.now(UTC)
    link.last_seen_badges_at = now
    db.commit()

    # Сколько осталось "новых" после этой отметки (на случай гонки).
    from app.student.models import UserBadge

    after = (
        db.execute(
            select(func.count(UserBadge.id)).where(
                UserBadge.user_id == student_id,
                UserBadge.awarded_at > now,
            )
        ).scalar()
        or 0
    )
    return now, int(after)
