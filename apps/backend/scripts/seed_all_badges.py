"""Sprint 3.11 — seed script: выдать все 20 бейджей заданному user_id.

Использование (на проде):
    docker compose exec -T backend bash -c "cd /app && PYTHONPATH=/app python /app/scripts/seed_all_badges.py <user_id>"

Или через docker exec в backend контейнер:
    docker compose exec -T backend bash -c "cd /app && PYTHONPATH=/app python -c '
from scripts.seed_all_badges import seed_all
from app.db.session import SessionLocal
print(seed_all(SessionLocal(), 62))
'"

Безопасно: использует ту же логику award_badge что и /api/v1/student/badges/evaluate.
Проверяет что бейдж ещё не выдан (idempotent). Сохраняет evidence.

Пример вывода:
    Awarded (10): ['hundred_solved', 'streak_3', ...]
    Already had (10): ['first_step', 'five_solved', ...]
"""
from __future__ import annotations

import json
import sys
from typing import Optional

# Sprint 3.11: явно импортируем все модели чтобы FK relationships
# между User / UserBadge / BadgeDefinition и другими таблицами
# были видны SQLAlchemy при инициализации.
from app.users import models as _users_models  # noqa: F401
from app.subjects import models as _subjects_models  # noqa: F401
from app.progress import models as _progress_models  # noqa: F401
from app.diagnostics import models as _diagnostics_models  # noqa: F401
from app.admin import models as _admin_models  # noqa: F401
from app.student import models as _student_models  # noqa: F401
from app.notifications import models as _notifications_models  # noqa: F401
from app.auth import password_reset_models as _password_reset_models  # noqa: F401
from app.sessions import models as _sessions_models  # noqa: F401
from app.cgm import models as _cgm_models  # noqa: F401
from app.invites import models as _invites_models  # noqa: F401

from sqlalchemy.orm import Session

from app.student.badges import (
    BADGES,
    award_badge,
    seed_badge_definitions,
)


# 20 slugs с фиктивным evidence (для теста UI — реальная проверка не нужна).
SEED_EVIDENCE = {
    # Количество решённых
    "first_step": {"total": 1},
    "five_solved": {"total": 5},
    "ten_solved": {"total": 10},
    "fifty_solved": {"total": 50},
    "hundred_solved": {"total": 100},
    "two_hundred_solved": {"total": 200},
    "three_hundred_solved": {"total": 300},
    "four_hundred_solved": {"total": 400},
    "five_hundred_solved": {"total": 500},
    "six_hundred_solved": {"total": 600},
    "seven_hundred_solved": {"total": 700},
    "eight_hundred_solved": {"total": 800},
    "nine_hundred_solved": {"total": 900},
    "thousand_solved": {"total": 1000},
    "fifteen_hundred_solved": {"total": 1500},
    # Усилие / качество
    "explained_in_own_words": {"quality_5_no_hint": 1},
    "five_quality_correct": {"quality_correct": 5},
    "twenty_quality_correct": {"quality_correct": 20},
    "fifty_quality_correct": {"quality_correct": 50},
    "returned_to_hard": {"returned_count": 1},
    "mastered_topic": {"mastery_avg": 0.85},
    "mastered_five_topics": {"count": 5},
    "all_basics": {"easy_solved": True},
    "review_count_10": {"review_count": 10},
    "review_count_50": {"review_count": 50},
    "asked_question": {"questions_asked": 1},
    # Серии
    "streak_3": {"streak_days": 3},
    "streak_7": {"streak_days": 7},
    "streak_14": {"streak_days": 14},
    "streak_30": {"streak_days": 30},
    "streak_60": {"streak_days": 60},
    "streak_100": {"streak_days": 100},
    "streak_180": {"streak_days": 180},
    "streak_365": {"streak_days": 365},
    "returned_after_pause": {"pause_days": 3},
    # Контекст
    "polymath_week": {"distinct_subjects_7d": 3},
    "early_bird": {"hour": 8},
    "night_owl": {"hour": 21},
    "weekend_warrior": {"weekend_count": 1},
    "perfect_five": {"consecutive_correct": 5},
    "ten_in_a_row": {"consecutive_correct": 10},
    "twenty_in_a_row": {"consecutive_correct": 20},
    "fifty_in_a_row": {"consecutive_correct": 50},
    "morning_streak_5": {"streak": 5},
    # Sprint 3.12: расширение effort/streak/context до 15 в каждой.
    # effort
    "correct_count_25": {"correct_count": 25},
    "correct_count_75": {"correct_count": 75},
    "correct_count_150": {"correct_count": 150},
    "correct_count_500": {"correct_count": 500},
    # streak
    "streak_45": {"streak_days": 45},
    "streak_correct_5": {"correct_streak": 5},
    "streak_correct_14": {"correct_streak": 14},
    "streak_correct_30": {"correct_streak": 30},
    "returned_twice": {"returns": 2},
    "returned_five": {"returns": 5},
    # context
    "lunch_learner": {"lunch": 1},
    "lunch_master": {"lunch": 10},
    "late_night_hero": {"late_night": 1},
    "weekend_regular_2": {"unique_weekends": 2},
    "weekend_master_8": {"unique_weekends": 8},
    "morning_streak_14": {"streak": 14},
}


def seed_all(db: Session, user_id: int) -> dict[str, list[str]]:
    """Выдать все 20 бейджей пользователю.

    Returns:
        {"awarded": [...], "already_had": [...]}.
    """
    seed_badge_definitions(db)

    awarded: list[str] = []
    already: list[str] = []
    for slug in SEED_EVIDENCE:
        evidence = SEED_EVIDENCE[slug]
        if award_badge(db, user_id, slug, evidence):
            awarded.append(slug)
        else:
            already.append(slug)
    return {"awarded": awarded, "already_had": already}


def seed_one(db: Session, user_id: int, slug: str) -> bool:
    """Выдать один бейдж. Returns True если новый, False если уже был."""
    seed_badge_definitions(db)
    evidence = SEED_EVIDENCE.get(slug, {"seeded": True})
    return award_badge(db, user_id, slug, evidence)


def main() -> None:
    if len(sys.argv) < 2:
        print("Использование: python seed_all_badges.py <user_id> [badge_slug]")
        print("  Примеры:")
        print("    python seed_all_badges.py 62              # все 20 бейджей")
        print("    python seed_all_badges.py 62 streak_3     # только streak_3")
        print(f"  Доступные badge slugs ({len(BADGES)}):")
        for b in BADGES:
            print(f"    - {b.slug:30s} {b.title}")
        sys.exit(1)

    from app.db.session import SessionLocal
    user_id = int(sys.argv[1])

    with SessionLocal() as db:
        if len(sys.argv) >= 3:
            slug = sys.argv[2]
            ok = seed_one(db, user_id, slug)
            print(f"  {slug}: {'awarded' if ok else 'already had'}")
        else:
            result = seed_all(db, user_id)
            print(f"  Awarded ({len(result['awarded'])}): {result['awarded']}")
            print(f"  Already had ({len(result['already_had'])}): {result['already_had']}")


if __name__ == "__main__":
    main()
