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
    # === Sprint 3.8 — gamification v2: streak + diversity + time-of-day ===
    # T1D-friendly: все streak-бейджи только положительные (за достижение).
    # Пропуск дня НЕ штрафуется — `returned_after_pause` наоборот ПООЩРЯЕТ
    # возвращение. Это сознательное отличие от типичной gamification.
    BadgeSpec(
        slug="streak_3",
        title="Три дня подряд",
        description="Активность 3 дня подряд. Первый ритм!",
        icon="🔥",
        criteria={"min_streak_days": 3},
    ),
    BadgeSpec(
        slug="streak_7",
        title="Неделя знаний",
        description="Активность 7 дней подряд. Стабильный ритм.",
        icon="🌟",
        criteria={"min_streak_days": 7},
    ),
    BadgeSpec(
        slug="streak_30",
        title="Месяц знаний",
        description="Активность 30 дней подряд. Настоящий мастер привычки.",
        icon="🏅",
        criteria={"min_streak_days": 30},
    ),
    BadgeSpec(
        slug="returned_after_pause",
        title="Возвращение",
        description="Ты вернулся после паузы ≥2 дней. Это и есть главное достижение.",
        icon="🌱",
        criteria={"returned_after_2plus_days": 1},
    ),
    BadgeSpec(
        slug="polymath_week",
        title="Полиматч недели",
        description="3+ разных предмета за последние 7 дней. Широкий кругозор.",
        icon="🧭",
        criteria={"min_subjects_in_7d": 3},
    ),
    BadgeSpec(
        slug="early_bird",
        title="Утренняя пташка",
        description="Задача решена утром (07:00–10:00 по локальному времени ученика).",
        icon="🌅",
        criteria={"time_of_day": "morning"},
    ),
    BadgeSpec(
        slug="night_owl",
        title="Сова",
        description="Задача решена вечером (20:00–23:00 по локальному времени ученика).",
        icon="🌙",
        criteria={"time_of_day": "evening"},
    ),
    BadgeSpec(
        slug="weekend_warrior",
        title="Герой выходных",
        description="Задача решена в выходной. Учёба без расписания.",
        icon="🎯",
        criteria={"weekend_attempt": 1},
    ),
    BadgeSpec(
        slug="perfect_five",
        title="Пятёрка подряд",
        description="5 правильных ответов подряд без единой ошибки.",
        icon="🎖️",
        criteria={"min_consecutive_correct": 5},
    ),
    BadgeSpec(
        slug="ten_in_a_row",
        title="Десятка подряд",
        description="10 правильных ответов подряд. Серия-мастерство.",
        icon="🏆",
        criteria={"min_consecutive_correct": 10},
    ),
    # === Sprint 3.11: расширение каталога ===
    # Категория «count» (количество решённых задач) — расширена до 15.
    # Категория «effort» (усилие и качество) — добавлены пороги по качеству,
    # mastery и SM-2 повторениям.
    # Категория «streak» (серии) — добавлены промежуточные milestone'ы.
    # Категория «context» (контекст и время) — расширены серии правильных.
    #
    # Все бейджи остаются ПОЗИТИВНЫМИ (за достижение), без штрафов за пропуск.
    # T1D-friendly: пропуск дня — это нормально, бейдж «returned_after_pause»
    # наоборот ПООЩРЯЕТ возвращение.
    # === Количество решённых (count): 200–1500 ===
    BadgeSpec(
        slug="two_hundred_solved",
        title="Двести задач",
        description="Решены 200 задач. Серьёзный объём.",
        icon="🎖️",
        criteria={"min_attempts": 200},
    ),
    BadgeSpec(
        slug="three_hundred_solved",
        title="Триста задач",
        description="Решены 300 задач. Методичная работа.",
        icon="🏅",
        criteria={"min_attempts": 300},
    ),
    BadgeSpec(
        slug="four_hundred_solved",
        title="Четыреста задач",
        description="Решены 400 задач. Системный подход.",
        icon="🎗️",
        criteria={"min_attempts": 400},
    ),
    BadgeSpec(
        slug="five_hundred_solved",
        title="Пятьсот задач",
        description="Решены 500 задач. Половина тысячи.",
        icon="💎",
        criteria={"min_attempts": 500},
    ),
    BadgeSpec(
        slug="six_hundred_solved",
        title="Шестьсот задач",
        description="Решены 600 задач. Ровный темп.",
        icon="🔷",
        criteria={"min_attempts": 600},
    ),
    BadgeSpec(
        slug="seven_hundred_solved",
        title="Семьсот задач",
        description="Решены 700 задач. Крепкая база.",
        icon="✨",
        criteria={"min_attempts": 700},
    ),
    BadgeSpec(
        slug="eight_hundred_solved",
        title="Восемьсот задач",
        description="Решены 800 задач. Большой опыт.",
        icon="🛡️",
        criteria={"min_attempts": 800},
    ),
    BadgeSpec(
        slug="nine_hundred_solved",
        title="Девятьсот задач",
        description="Решены 900 задач. Почти тысяча.",
        icon="⚜️",
        criteria={"min_attempts": 900},
    ),
    BadgeSpec(
        slug="thousand_solved",
        title="Тысяча задач",
        description="Решены 1000 задач. Тысяча!",
        icon="👑",
        criteria={"min_attempts": 1000},
    ),
    BadgeSpec(
        slug="fifteen_hundred_solved",
        title="Полторы тысячи",
        description="Решены 1500 задач. Уровень мастера.",
        icon="🌠",
        criteria={"min_attempts": 1500},
    ),
    # === Усилие и качество (effort): больше порогов ===
    BadgeSpec(
        slug="five_quality_correct",
        title="Пятёрка безупречности",
        description="5 точных правильных ответов (score ≥ 0.9). Качество.",
        icon="✨",
        criteria={"min_quality_correct": 5},
    ),
    BadgeSpec(
        slug="twenty_quality_correct",
        title="Двадцать точных",
        description="20 точных правильных ответов. Стабильность.",
        icon="💫",
        criteria={"min_quality_correct": 20},
    ),
    BadgeSpec(
        slug="fifty_quality_correct",
        title="Полтинник мастерства",
        description="50 точных правильных ответов. Настоящий мастер.",
        icon="🌟",
        criteria={"min_quality_correct": 50},
    ),
    BadgeSpec(
        slug="mastered_five_topics",
        title="Пять освоенных тем",
        description="5 тем с mastery ≥ 80%. Темы пройдены.",
        icon="🏛️",
        criteria={"min_mastered_topics": 5},
    ),
    BadgeSpec(
        slug="review_count_10",
        title="Повторяй-ка",
        description="10 повторений по spaced repetition (SM-2). Память крепнет.",
        icon="📖",
        criteria={"min_review_count": 10},
    ),
    BadgeSpec(
        slug="review_count_50",
        title="Крепкая память",
        description="50 повторений по SM-2. Темы держатся в голове.",
        icon="📚",
        criteria={"min_review_count": 50},
    ),
    # === Серии (streak): промежуточные milestones ===
    BadgeSpec(
        slug="streak_14",
        title="Две недели",
        description="Активность 14 дней подряд. Устоявшийся ритм.",
        icon="⭐",
        criteria={"min_streak_days": 14},
    ),
    BadgeSpec(
        slug="streak_60",
        title="Два месяца",
        description="Активность 60 дней подряд. Стабильность.",
        icon="🏆",
        criteria={"min_streak_days": 60},
    ),
    BadgeSpec(
        slug="streak_100",
        title="Сотня дней",
        description="Активность 100 дней подряд. Серьёзный результат.",
        icon="💯",
        criteria={"min_streak_days": 100},
    ),
    BadgeSpec(
        slug="streak_180",
        title="Полгода",
        description="Активность 180 дней подряд. Полгода без пауз.",
        icon="🌞",
        criteria={"min_streak_days": 180},
    ),
    BadgeSpec(
        slug="streak_365",
        title="Целый год",
        description="Активность 365 дней подряд. Год знаний.",
        icon="🎊",
        criteria={"min_streak_days": 365},
    ),
    # === Контекст (context): расширенные серии правильных + утро ===
    BadgeSpec(
        slug="twenty_in_a_row",
        title="Двадцатка подряд",
        description="20 правильных ответов подряд. Серия-мастерство.",
        icon="👑",
        criteria={"min_consecutive_correct": 20},
    ),
    BadgeSpec(
        slug="fifty_in_a_row",
        title="Полтинник-серия",
        description="50 правильных ответов подряд. Уровень легенды.",
        icon="🌠",
        criteria={"min_consecutive_correct": 50},
    ),
    BadgeSpec(
        slug="morning_streak_5",
        title="Утренняя серия",
        description="5 дней подряд с утренней активностью (07:00–10:00).",
        icon="☀️",
        criteria={"min_morning_streak_days": 5},
    ),
    # === Sprint 3.12: расширение effort/streak/context до 15 в каждой ===
    # effort (11 → 15): правильные ответы по порогам + weekend-регулярность.
    BadgeSpec(
        slug="correct_count_25",
        title="Двадцать пять правильных",
        description="25 правильных ответов. Базис уверенности.",
        icon="🎓",
        criteria={"min_correct_count": 25},
    ),
    BadgeSpec(
        slug="correct_count_75",
        title="Семьдесят пять правильных",
        description="75 правильных ответов. Точный фундамент.",
        icon="📐",
        criteria={"min_correct_count": 75},
    ),
    BadgeSpec(
        slug="correct_count_150",
        title="Полтораста правильных",
        description="150 правильных ответов. Серьёзная точность.",
        icon="📊",
        criteria={"min_correct_count": 150},
    ),
    BadgeSpec(
        slug="correct_count_500",
        title="Полтысячи правильных",
        description="500 правильных ответов. Уровень эксперта.",
        icon="🏅",
        criteria={"min_correct_count": 500},
    ),
    # streak (9 → 15): промежуточные milestones + возвраты.
    BadgeSpec(
        slug="streak_45",
        title="Полтора месяца",
        description="Активность 45 дней подряд. Между месяцем и двумя.",
        icon="✨",
        criteria={"min_streak_days": 45},
    ),
    BadgeSpec(
        slug="streak_correct_5",
        title="Пять точных дней",
        description="5 дней подряд где хотя бы 1 ответ правильный. Точный ритм.",
        icon="🎯",
        criteria={"min_correct_streak_days": 5},
    ),
    BadgeSpec(
        slug="streak_correct_14",
        title="Две недели точности",
        description="14 дней подряд с правильными ответами. Точность — привычка.",
        icon="✦",
        criteria={"min_correct_streak_days": 14},
    ),
    BadgeSpec(
        slug="streak_correct_30",
        title="Месяц точности",
        description="30 дней подряд с правильными ответами. Уровень мастера.",
        icon="🎖️",
        criteria={"min_correct_streak_days": 30},
    ),
    BadgeSpec(
        slug="returned_twice",
        title="Два возврата",
        description="2 раза вернулся после паузы ≥2 дней. Упорство.",
        icon="🌿",
        criteria={"min_pause_return_count": 2},
    ),
    BadgeSpec(
        slug="returned_five",
        title="Пять возвратов",
        description="5 раз вернулся после паузы ≥2 дней. Неугасающий интерес.",
        icon="🌳",
        criteria={"min_pause_return_count": 5},
    ),
    # context (9 → 15): lunch/late-night + weekend_unique + morning_streak.
    BadgeSpec(
        slug="lunch_learner",
        title="Обеденный ученик",
        description="Задача решена в обед (12:00–14:00). Учёба в перерыве.",
        icon="🍱",
        criteria={"min_lunch_count": 1},
    ),
    BadgeSpec(
        slug="lunch_master",
        title="Обеденный мастер",
        description="10 задач решено в обед (12:00–14:00). Привычка.",
        icon="🍱",
        criteria={"min_lunch_count": 10},
    ),
    BadgeSpec(
        slug="late_night_hero",
        title="Полуночник",
        description="Задача решена ночью (23:00–02:00). Время — не помеха.",
        icon="🌃",
        criteria={"min_late_night_count": 1},
    ),
    BadgeSpec(
        slug="weekend_regular_2",
        title="Два выходных",
        description="Активность в 2 разных выходных дня. Регулярность.",
        icon="📅",
        criteria={"min_weekend_unique_dates": 2},
    ),
    BadgeSpec(
        slug="weekend_master_8",
        title="Мастер выходных",
        description="Активность в 8 разных выходных дней. Учёба без расписания.",
        icon="🏖️",
        criteria={"min_weekend_unique_dates": 8},
    ),
    BadgeSpec(
        slug="morning_streak_14",
        title="Утренний ритм",
        description="14 дней подряд с утренней активностью. Утро — время для учения.",
        icon="🌅",
        criteria={"min_morning_streak_days": 14},
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
    stats: dict | None = None,
) -> list[str]:
    """Проверить статистику и присудить подходящие баджи.

    Args:
        db: SQLAlchemy session.
        user_id: пользователь.
        stats: статистика (если None — собирается автоматически через collect_stats).

    Возвращает список slug'ов баджей, присуждённых в этом вызове.
    Sprint 3.8: добавлены streak/diversity/time-of-day/consecutive_correct.
    Sprint 3.11: расширен каталог (53 бейджа) — count/streak/context thresholds.
    """
    seed_badge_definitions(db)  # idempotent
    if stats is None:
        stats = collect_stats(db, user_id)
    awarded: list[str] = []
    total = stats.get("total_attempts", 0)

    # first_step, five_solved, ten_solved, fifty_solved, hundred_solved,
    # 200..1500 (Sprint 3.11).
    count_thresholds = [
        ("first_step", 1),
        ("five_solved", 5),
        ("ten_solved", 10),
        ("fifty_solved", 50),
        ("hundred_solved", 100),
        ("two_hundred_solved", 200),
        ("three_hundred_solved", 300),
        ("four_hundred_solved", 400),
        ("five_hundred_solved", 500),
        ("six_hundred_solved", 600),
        ("seven_hundred_solved", 700),
        ("eight_hundred_solved", 800),
        ("nine_hundred_solved", 900),
        ("thousand_solved", 1000),
        ("fifteen_hundred_solved", 1500),
    ]
    for slug, threshold in count_thresholds:
        if total >= threshold:
            if award_badge(db, user_id, slug, {"total": total}):
                awarded.append(slug)

    # explained_in_own_words
    if stats.get("quality_5_no_hint", 0) >= 1:
        if award_badge(db, user_id, "explained_in_own_words"):
            awarded.append("explained_in_own_words")

    # quality_correct thresholds (Sprint 3.11) — точные правильные ответы.
    quality_correct = stats.get("quality_correct_count", 0)
    for slug, threshold in [
        ("five_quality_correct", 5),
        ("twenty_quality_correct", 20),
        ("fifty_quality_correct", 50),
    ]:
        if quality_correct >= threshold:
            if award_badge(db, user_id, slug, {"quality_correct": quality_correct}):
                awarded.append(slug)

    # returned_to_hard
    if stats.get("returned_to_incorrect", 0) >= 1:
        if award_badge(db, user_id, "returned_to_hard"):
            awarded.append("returned_to_hard")

    # mastered_topic
    if stats.get("max_mastery", 0.0) >= 0.8:
        if award_badge(db, user_id, "mastered_topic", {"max_mastery": stats["max_mastery"]}):
            awarded.append("mastered_topic")

    # mastered_five_topics (Sprint 3.11) — 5 тем с mastery ≥80%.
    if stats.get("mastered_topics_count", 0) >= 5:
        if award_badge(db, user_id, "mastered_five_topics", {"count": stats["mastered_topics_count"]}):
            awarded.append("mastered_five_topics")

    # Sprint 3.12: correct_count thresholds — точные правильные ответы.
    cc = stats.get("correct_count", 0)
    for slug, threshold in [
        ("correct_count_25", 25),
        ("correct_count_75", 75),
        ("correct_count_150", 150),
        ("correct_count_500", 500),
    ]:
        if cc >= threshold:
            if award_badge(db, user_id, slug, {"correct_count": cc}):
                awarded.append(slug)

    # all_basics (≥1 easy solved)
    if stats.get("easy_solved", 0) >= 1:
        if award_badge(db, user_id, "all_basics"):
            awarded.append("all_basics")

    # asked_question
    if stats.get("questions_to_ai", 0) >= 1:
        if award_badge(db, user_id, "asked_question"):
            awarded.append("asked_question")

    # review_count thresholds (Sprint 3.11) — SM-2 повторения.
    review_total = stats.get("review_count_total", 0)
    for slug, threshold in [
        ("review_count_10", 10),
        ("review_count_50", 50),
    ]:
        if review_total >= threshold:
            if award_badge(db, user_id, slug, {"review_count": review_total}):
                awarded.append(slug)

    # === Sprint 3.8: gamification v2 ===
    # streak-based (позитивные — за достижение)
    streak = stats.get("current_streak_days", 0)
    for slug, threshold in [
        ("streak_3", 3),
        ("streak_7", 7),
        ("streak_14", 14),
        ("streak_30", 30),
        ("streak_45", 45),
        ("streak_60", 60),
        ("streak_100", 100),
        ("streak_180", 180),
        ("streak_365", 365),
    ]:
        if streak >= threshold:
            if award_badge(db, user_id, slug, {"streak": streak}):
                awarded.append(slug)

    # Sprint 3.12: streak_correct_N — дни подряд с правильным ответом.
    correct_streak = stats.get("correct_streak_days", 0)
    for slug, threshold in [
        ("streak_correct_5", 5),
        ("streak_correct_14", 14),
        ("streak_correct_30", 30),
    ]:
        if correct_streak >= threshold:
            if award_badge(db, user_id, slug, {"correct_streak": correct_streak}):
                awarded.append(slug)

    # Sprint 3.12: pause_return_count — сколько раз был пропуск ≥2 дней.
    prc = stats.get("pause_return_count", 0)
    for slug, threshold in [
        ("returned_twice", 2),
        ("returned_five", 5),
    ]:
        if prc >= threshold:
            if award_badge(db, user_id, slug, {"returns": prc}):
                awarded.append(slug)

    # returned_after_pause — НЕ штраф, а позитив: «ты вернулся»
    if stats.get("returned_after_pause", 0) >= 1:
        if award_badge(db, user_id, "returned_after_pause"):
            awarded.append("returned_after_pause")

    # polymath_week: 3+ предмета за 7 дней
    if stats.get("subjects_in_last_7d", 0) >= 3:
        if award_badge(db, user_id, "polymath_week", {
            "subjects": stats["subjects_in_last_7d"],
        }):
            awarded.append("polymath_week")

    # time-of-day (по локальному TZ ученика)
    if stats.get("morning_attempt", 0) >= 1:
        if award_badge(db, user_id, "early_bird"):
            awarded.append("early_bird")
    if stats.get("evening_attempt", 0) >= 1:
        if award_badge(db, user_id, "night_owl"):
            awarded.append("night_owl")

    # weekend_attempt
    if stats.get("weekend_attempt", 0) >= 1:
        if award_badge(db, user_id, "weekend_warrior"):
            awarded.append("weekend_warrior")

    # Sprint 3.12: weekend_unique_dates thresholds.
    wud = stats.get("weekend_unique_dates", 0)
    for slug, threshold in [
        ("weekend_regular_2", 2),
        ("weekend_master_8", 8),
    ]:
        if wud >= threshold:
            if award_badge(db, user_id, slug, {"unique_weekends": wud}):
                awarded.append(slug)

    # Sprint 3.12: lunch_learner, lunch_master.
    lunch_n = stats.get("lunch_count", 0)
    for slug, threshold in [
        ("lunch_learner", 1),
        ("lunch_master", 10),
    ]:
        if lunch_n >= threshold:
            if award_badge(db, user_id, slug, {"lunch": lunch_n}):
                awarded.append(slug)

    # Sprint 3.12: late_night_hero.
    if stats.get("late_night_count", 0) >= 1:
        if award_badge(db, user_id, "late_night_hero"):
            awarded.append("late_night_hero")

    # consecutive_correct (5, 10, 20, 50)
    cc = stats.get("max_consecutive_correct", 0)
    for slug, threshold in [
        ("perfect_five", 5),
        ("ten_in_a_row", 10),
        ("twenty_in_a_row", 20),
        ("fifty_in_a_row", 50),
    ]:
        if cc >= threshold:
            if award_badge(db, user_id, slug, {"run": cc}):
                awarded.append(slug)

    # morning_streak_5 (Sprint 3.11) — 5 дней подряд с утренней активностью.
    ms = stats.get("morning_streak_days", 0)
    for slug, threshold in [
        ("morning_streak_5", 5),
        ("morning_streak_14", 14),
    ]:
        if ms >= threshold:
            if award_badge(db, user_id, slug, {"streak": ms}):
                awarded.append(slug)

    return awarded


def collect_stats(db: Session, user_id: int) -> dict:
    """Собрать статистику пользователя из БД (1 запрос на показатель).

    Sprint 3.8: добавлены поля для gamification v2:
    - current_streak_days: текущая серия (считаем в Python через _compute_streak)
    - returned_after_pause: 1 если последний attempt был после паузы ≥2 дней
    - subjects_in_last_7d: кол-во уникальных subject_id за 7 дней
    - morning/evening/weekend: 1 если хотя бы один attempt в это окно
    - max_consecutive_correct: длина самой длинной серии правильных ответов
    """
    from datetime import datetime, timedelta, timezone
    from zoneinfo import ZoneInfo

    from app.config import get_settings
    from app.parents.service import _compute_streak
    from app.progress import models as prog_models

    s = db
    # total_attempts
    total = s.execute(
        select(func.count(prog_models.Attempt.id)).where(
            prog_models.Attempt.user_id == user_id
        )
    ).scalar() or 0

    # quality_5: все правильные attempts (proxy без колонки hint)
    quality_5_no_hint = s.execute(
        select(func.count(prog_models.Attempt.id)).where(
            prog_models.Attempt.user_id == user_id,
            prog_models.Attempt.is_correct == True,  # noqa: E712
        )
    ).scalar() or 0

    # Sprint 3.11: quality_correct — точные правильные ответы (score ≥ 0.9).
    # Используется для бейджей five/twenty/fifty_quality_correct.
    quality_correct_count = s.execute(
        select(func.count(prog_models.Attempt.id)).where(
            prog_models.Attempt.user_id == user_id,
            prog_models.Attempt.is_correct == True,  # noqa: E712
            prog_models.Attempt.score >= 0.9,
        )
    ).scalar() or 0

    # Sprint 3.11: review_count_total — сумма SM-2 повторений по всем темам.
    # Используется для бейджей review_count_10 / review_count_50.
    review_count_total = s.execute(
        select(func.coalesce(func.sum(prog_models.Progress.review_count), 0)).where(
            prog_models.Progress.user_id == user_id
        )
    ).scalar() or 0

    # Sprint 3.11: mastered_topics_count — кол-во тем с mastery ≥ 0.8.
    mastered_topics_count = s.execute(
        select(func.count(prog_models.Progress.id)).where(
            prog_models.Progress.user_id == user_id,
            prog_models.Progress.mastery_score >= 0.8,
        )
    ).scalar() or 0

    # returned_to_incorrect: если есть хотя бы 1 ошибка + 1 успех
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

    # easy_solved / questions_to_ai proxies
    easy_solved = total
    questions_to_ai = total

    # === Sprint 3.8: gamification v2 stats ===
    # Загружаем все attempts с временной меткой — для streak + time-of-day +
    # consecutive_correct. На пилотной нагрузке (<10k attempts на user) это OK.
    all_attempts = s.execute(
        select(
            prog_models.Attempt.created_at,
            prog_models.Attempt.is_correct,
            prog_models.Attempt.topic_id,
        )
        .where(prog_models.Attempt.user_id == user_id)
        .order_by(prog_models.Attempt.created_at.asc())
    ).all()

    # TZ: используем настройку приложения (Europe/Moscow по дефолту).
    student_tz = ZoneInfo(get_settings().student_timezone or "Europe/Moscow")
    today = datetime.now(student_tz).date()

    # unique active dates (для streak)
    active_dates: set[str] = set()
    # (date, subject_id) → для diversity за 7 дней
    # Связь Attempt.topic_id → subject_id через Section
    from app.subjects import models as subj_models

    subject_ids_by_topic: dict[int, int] = {}
    topic_ids = {row.topic_id for row in all_attempts if row.topic_id is not None}
    if topic_ids:
        rows = s.execute(
            select(subj_models.Topic.id, subj_models.Section.subject_id)
            .join(subj_models.Section, subj_models.Topic.section_id == subj_models.Section.id)
            .where(subj_models.Topic.id.in_(topic_ids))
        ).all()
        for tid, sid in rows:
            subject_ids_by_topic[tid] = sid

    # time-of-day buckets
    morning_count = 0  # 07:00–10:00
    evening_count = 0  # 20:00–23:00
    weekend_count = 0  # Sat/Sun
    active_dates_in_7d: set[str] = set()
    subjects_in_7d: set[int] = set()
    seven_days_ago = today - timedelta(days=7)

    # Sprint 3.11: для бейджа morning_streak_5 — множество дат с утренней
    # активностью (07:00–10:00 по локальному TZ ученика).
    morning_dates: set[str] = set()

    # Sprint 3.12: lunch (12:00–14:00) и late-night (23:00–02:00).
    lunch_count = 0
    late_night_count = 0
    # Уникальные weekend-даты (для бейджей weekend_2x, weekend_4x).
    weekend_unique_dates: set[str] = set()
    # Даты с хотя бы одним правильным ответом (для streak_correct_N).
    correct_dates: set[str] = set()
    # Кол-во возвращений после паузы ≥2 дней за всё время (для returned_Nx).
    pause_return_count = 0

    # consecutive correct (по created_at asc, ищем самую длинную серию is_correct=True)
    max_consecutive_correct = 0
    current_run = 0

    for row in all_attempts:
        ts = row.created_at
        if ts is None:
            continue
        # ts хранится в UTC (TIMESTAMP WITHOUT TZ); конвертим в student TZ
        if isinstance(ts, datetime):
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            local_dt = ts.astimezone(student_tz)
            d = local_dt.date()
            active_dates.add(d.isoformat())
            if d >= seven_days_ago:
                active_dates_in_7d.add(d.isoformat())
                sid = subject_ids_by_topic.get(row.topic_id or -1)
                if sid is not None:
                    subjects_in_7d.add(sid)
            # time-of-day
            h = local_dt.hour
            if 7 <= h < 10:
                morning_count += 1
                morning_dates.add(d.isoformat())
            elif 12 <= h < 14:
                # Sprint 3.12: lunch (12:00–14:00).
                lunch_count += 1
            elif 20 <= h < 23:
                evening_count += 1
            elif h >= 23 or h < 2:
                # Sprint 3.12: late-night (23:00–02:00 следующего дня).
                late_night_count += 1
            # weekend
            wd = local_dt.weekday()  # 0=Mon, 6=Sun
            if wd >= 5:
                weekend_count += 1
                weekend_unique_dates.add(d.isoformat())

        # consecutive correct: считаем по исходному (asc) порядку
        if row.is_correct:
            current_run += 1
            if current_run > max_consecutive_correct:
                max_consecutive_correct = current_run
            # Sprint 3.12: дата с правильным ответом — для streak_correct_N.
            if isinstance(ts, datetime):
                if ts.tzinfo is None:
                    ts_utc = ts.replace(tzinfo=timezone.utc)
                else:
                    ts_utc = ts
                correct_dates.add(ts_utc.astimezone(student_tz).date().isoformat())
        else:
            current_run = 0

    current_streak_days, _, _ = _compute_streak(active_dates, today.isoformat())

    # Sprint 3.11: morning_streak_days — текущая серия дней подряд с утренней
    # активностью. Используем ту же логику _compute_streak что и для общей серии.
    morning_streak_days, _, _ = _compute_streak(morning_dates, today.isoformat())

    # Sprint 3.12: correct_streak_days — текущая серия дней подряд где был
    # хотя бы 1 правильный ответ (для streak_correct_5/14/30).
    correct_streak_days, _, _ = _compute_streak(correct_dates, today.isoformat())

    # Sprint 3.12: pause_return_count — сколько раз за всё время был пропуск
    # ≥2 дней между двумя активными датами. Считаем по отсортированному списку.
    if len(active_dates) >= 2:
        sorted_dates = sorted(active_dates)
        for i in range(1, len(sorted_dates)):
            prev_d = today.__class__.fromisoformat(sorted_dates[i - 1])
            curr_d = today.__class__.fromisoformat(sorted_dates[i])
            if (curr_d - prev_d).days >= 2:
                pause_return_count += 1

    # returned_after_pause: предпоследний attempt был ≥2 дней назад, последний — сегодня.
    # Простой proxy: если total >= 2 и last attempt <= today, и (today - second_last date) >= 2.
    returned_after_pause = 0
    if len(active_dates) >= 2:
        sorted_dates = sorted(active_dates)
        last = sorted_dates[-1]
        second_last = sorted_dates[-2]
        last_d = today.__class__.fromisoformat(last)
        prev_d = today.__class__.fromisoformat(second_last)
        if last_d == today and (last_d - prev_d).days >= 2:
            returned_after_pause = 1

    return {
        "total_attempts": int(total),
        "quality_5_no_hint": int(quality_5_no_hint),
        "returned_to_incorrect": int(returned_to_incorrect),
        "max_mastery": max_mastery,
        "easy_solved": int(easy_solved),
        "questions_to_ai": int(questions_to_ai),
        # Sprint 3.8 gamification v2:
        "current_streak_days": int(current_streak_days),
        "returned_after_pause": int(returned_after_pause),
        "subjects_in_last_7d": len(subjects_in_7d),
        "morning_attempt": 1 if morning_count >= 1 else 0,
        "evening_attempt": 1 if evening_count >= 1 else 0,
        "weekend_attempt": 1 if weekend_count >= 1 else 0,
        "max_consecutive_correct": int(max_consecutive_correct),
        # Sprint 3.11 — расширенные метрики для новых бейджей:
        "quality_correct_count": int(quality_correct_count),
        "review_count_total": int(review_count_total),
        "mastered_topics_count": int(mastered_topics_count),
        "morning_streak_days": int(morning_streak_days),
        # Sprint 3.12 — ещё метрики для расширения каталога:
        "lunch_count": int(lunch_count),
        "late_night_count": int(late_night_count),
        "weekend_unique_dates": len(weekend_unique_dates),
        "correct_streak_days": int(correct_streak_days),
        "pause_return_count": int(pause_return_count),
        # Также явно прокинем correct_count и easy_correct_count для новых effort бейджей.
        "correct_count": int(quality_5_no_hint),  # alias для total correct
    }
