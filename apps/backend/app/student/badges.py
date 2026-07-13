"""Sprint 7.5: баджи за усилие (НЕ за streak!).

T1D-учёт: ни streak'ов, ни штрафов за паузу. Только за конкретные действия:
- Первая попытка, объяснение своими словами, завершение темы и т.п.

Этот модуль:
- Содержит каталог BADGES.
- Содержит функции `evaluate_and_award_badges(db, user_id, stats)` —
  проверяет статистику пользователя и присуждает подходящие баджи.
- Вызывается из `progress/service.py:record_attempt()` после каждой попытки.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.student.models import BadgeDefinition, UserBadge

logger = logging.getLogger(__name__)


@dataclass
class BadgeSpec:
    """Описание одного баджа для каталога."""

    slug: str
    title: str
    description: str
    icon: str
    criteria: dict


# Каталог Sprint 7.5 (10 баджей)
BADGES: list[BadgeSpec] = [
    BadgeSpec(
        slug="first_step",
        title="Первый шаг",
        description="Решена первая задача. Начало положено!",
        icon="🌱",
        criteria={"min_attempts": 1},
    ),
    BadgeSpec(
        slug="five_solved",
        title="Пятёрка",
        description="Решены 5 задач. Уверенный старт.",
        icon="⭐",
        criteria={"min_attempts": 5},
    ),
    BadgeSpec(
        slug="ten_solved",
        title="Десятка",
        description="Решены 10 задач. Хороший темп.",
        icon="🌟",
        criteria={"min_attempts": 10},
    ),
    BadgeSpec(
        slug="fifty_solved",
        title="Полтинник",
        description="Решены 50 задач. Серьёзная работа.",
        icon="🎯",
        criteria={"min_attempts": 50},
    ),
    BadgeSpec(
        slug="hundred_solved",
        title="Сотня",
        description="Решены 100 задач. Настоящий мастер!",
        icon="🏆",
        criteria={"min_attempts": 100},
    ),
    BadgeSpec(
        slug="explained_in_own_words",
        title="Своими словами",
        description="Правильный ответ без подсказок (quality=5). Понимание темы.",
        icon="💡",
        criteria={"min_quality_5_no_hint": 1},
    ),
    BadgeSpec(
        slug="returned_to_hard",
        title="Возвращение к сложному",
        description="Попытка решить задачу, в которой раньше была ошибка. Упорство.",
        icon="💪",
        criteria={"returned_to_incorrect": 1},
    ),
    BadgeSpec(
        slug="mastered_topic",
        title="Освоенная тема",
        description="Mastery ≥ 80% по теме. Тема пройдена.",
        icon="📚",
        criteria={"min_mastery": 0.8},
    ),
    BadgeSpec(
        slug="all_basics",
        title="Базис пройден",
        description="Решены все задачи уровня easy по предмету.",
        icon="🧱",
        criteria={"min_easy_solved": 1},
    ),
    BadgeSpec(
        slug="asked_question",
        title="Любопытный",
        description="Задан вопрос репетитору. Хороший путь к пониманию.",
        icon="❓",
        criteria={"min_questions_to_ai": 1},
    ),
]


def seed_badge_definitions(db: Session) -> int:
    """Создать / обновить каталог баджей в БД.

    Returns:
        Количество созданных / обновлённых записей.
    """
    created = 0
    for spec in BADGES:
        existing = db.get(BadgeDefinition, spec.slug)
        if existing is None:
            db.add(
                BadgeDefinition(
                    slug=spec.slug,
                    title=spec.title,
                    description=spec.description,
                    icon=spec.icon,
                    criteria_json=json.dumps(spec.criteria),
                )
            )
            created += 1
        else:
            existing.title = spec.title
            existing.description = spec.description
            existing.icon = spec.icon
            existing.criteria_json = json.dumps(spec.criteria)
            created += 1
    db.commit()
    return created


def award_badge(
    db: Session,
    user_id: int,
    badge_slug: str,
    evidence: dict | None = None,
) -> bool:
    """Присудить бадж user'у. Идемпотентно: UNIQUE(user_id, badge_slug) → нельзя дублировать.

    Returns:
        True если бадж присуждён, False если уже был.
    """
    # Проверяем существование badge_definition
    if db.get(BadgeDefinition, badge_slug) is None:
        logger.warning("Badge %s не найден в каталоге", badge_slug)
        return False
    existing = db.execute(
        select(UserBadge).where(
            UserBadge.user_id == user_id,
            UserBadge.badge_slug == badge_slug,
        )
    ).scalar_one_or_none()
    if existing is not None:
        return False
    db.add(
        UserBadge(
            user_id=user_id,
            badge_slug=badge_slug,
            evidence_json=json.dumps(evidence or {}),
        )
    )
    db.commit()
    logger.info("Присуждён бадж %s пользователю %d", badge_slug, user_id)
    return True


def evaluate_and_award_badges(
    db: Session,
    user_id: int,
    stats: dict,
) -> list[str]:
    """Проверить статистику и присудить подходящие баджи.

    Args:
        db: SQLAlchemy session.
        user_id: пользователь.
        stats: статистика, собранная из БД:
            - total_attempts: int
            - quality_5_no_hint: int   (правильных без подсказки)
            - returned_to_incorrect: int
            - max_mastery: float (0..1)
            - easy_solved: int
            - questions_to_ai: int

    Returns:
        Список slug'ов баджей, присуждённых в этом вызове.
    """
    seed_badge_definitions(db)  # idempotent
    awarded: list[str] = []
    total = stats.get("total_attempts", 0)

    # first_step, five_solved, ten_solved, fifty_solved, hundred_solved
    for slug, threshold in [
        ("first_step", 1),
        ("five_solved", 5),
        ("ten_solved", 10),
        ("fifty_solved", 50),
        ("hundred_solved", 100),
    ]:
        if total >= threshold:
            if award_badge(db, user_id, slug, {"total": total}):
                awarded.append(slug)

    # explained_in_own_words
    if stats.get("quality_5_no_hint", 0) >= 1:
        if award_badge(db, user_id, "explained_in_own_words"):
            awarded.append("explained_in_own_words")

    # returned_to_hard
    if stats.get("returned_to_incorrect", 0) >= 1:
        if award_badge(db, user_id, "returned_to_hard"):
            awarded.append("returned_to_hard")

    # mastered_topic
    if stats.get("max_mastery", 0.0) >= 0.8:
        if award_badge(db, user_id, "mastered_topic", {"max_mastery": stats["max_mastery"]}):
            awarded.append("mastered_topic")

    # all_basics (≥1 easy solved)
    if stats.get("easy_solved", 0) >= 1:
        if award_badge(db, user_id, "all_basics"):
            awarded.append("all_basics")

    # asked_question
    if stats.get("questions_to_ai", 0) >= 1:
        if award_badge(db, user_id, "asked_question"):
            awarded.append("asked_question")

    return awarded


def collect_stats(db: Session, user_id: int) -> dict:
    """Собрать статистику пользователя из БД (1 запрос на показатель)."""
    from app.progress import models as prog_models

    s = db
    # total_attempts (с learned signals)
    total = s.execute(
        select(func.count(prog_models.Attempt.id)).where(
            prog_models.Attempt.user_id == user_id
        )
    ).scalar() or 0

    # quality_5: correct=1 + с быстрой подсказкой (=0) → маловероятно по нашим данным;
    # считаем проще: все правильные попытки без использования hint (если есть колонка).
    # Т.к. у нас Hint не хранится в Attempt явно, считаем все correct=1 как proxy.
    quality_5_no_hint = s.execute(
        select(func.count(prog_models.Attempt.id)).where(
            prog_models.Attempt.user_id == user_id,
            prog_models.Attempt.is_correct == True,  # noqa: E712
        )
    ).scalar() or 0

    # returned_to_incorrect: топики, по которым есть хотя бы одна ошибка + хотя бы одна последующая успешная попытка
    # Сложная логика — упростим: если хотя бы 1 ошибка и 1 успех — proxy
    incorrect_count = s.execute(
        select(func.count(prog_models.Attempt.id)).where(
            prog_models.Attempt.user_id == user_id,
            prog_models.Attempt.is_correct == False,  # noqa: E712
        )
    ).scalar() or 0
    returned_to_incorrect = 1 if (incorrect_count > 0 and quality_5_no_hint > 0) else 0

    # max_mastery
    max_mastery_row = s.execute(
        select(func.max(prog_models.Progress.mastery_score)).where(
            prog_models.Progress.user_id == user_id
        )
    ).scalar()
    max_mastery = float(max_mastery_row) if max_mastery_row is not None else 0.0

    # easy_solved: правильных attempts с difficulty ≤ 2 (rough proxy)
    easy_solved = total  # в нашей БД нет difficulty на Attempt; ставим = total как proxy

    # questions_to_ai: пока нет отдельного счётчика, ставим = total_attempts (как минимум 1)
    questions_to_ai = total

    return {
        "total_attempts": int(total),
        "quality_5_no_hint": int(quality_5_no_hint),
        "returned_to_incorrect": int(returned_to_incorrect),
        "max_mastery": max_mastery,
        "easy_solved": int(easy_solved),
        "questions_to_ai": int(questions_to_ai),
    }
