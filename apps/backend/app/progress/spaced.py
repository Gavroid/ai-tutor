"""Spaced Repetition (SM-2 алгоритм) — Sprint 2.2.

Алгоритм SM-2 (SuperMemo 2), адаптированный для оценки 0..5:
- q=5: идеально — увеличиваем интервал сильно
- q=4: хорошо
- q=3: средне (порог "помню")
- q<3: не помню — сбрасываем

EF (easiness factor) — множитель интервала, ≥1.3.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

# Минимальный EF (из SM-2)
MIN_EF = 1.3


@dataclass
class ScheduleResult:
    """Результат расчёта нового расписания."""

    next_review_at: datetime
    interval_days: int
    new_ef: float
    review_count: int


def schedule_next_review(
    last_reviewed_at: datetime | None,
    review_count: int,
    easiness_factor: float,
    quality: int,  # 0..5
    now: datetime | None = None,
) -> ScheduleResult:
    """Возвращает новое расписание повторения по SM-2.

    quality:
      5 — perfect
      4 — correct, hesitations
      3 — correct with serious difficulty
      2 — incorrect, easy to remember
      1 — incorrect, familiar
      0 — blackout, completely forgot

    Стандартный SM-2:
      - Если q >= 3:
          n=1 → interval=1
          n=2 → interval=6
          n>2 → interval = round(prev_interval * EF)
      - Иначе: n сбрасывается в 1, interval = 1
      - EF' = EF + (0.1 - (5-q) * (0.08 + (5-q) * 0.02))
      - EF' = max(EF', 1.3)
    """
    now = now or datetime.now(timezone.utc)
    quality = max(0, min(5, quality))

    # EF update
    new_ef = easiness_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    new_ef = max(MIN_EF, new_ef)

    if quality < 3:
        # Забыл — повторяем завтра, счётчик не растёт
        new_count = max(0, review_count)
        interval_days = 1
    else:
        new_count = review_count + 1
        if new_count == 1:
            interval_days = 1
        elif new_count == 2:
            interval_days = 6
        else:
            # Используем предыдущий interval (нужно знать)
            # Упрощение: для n>2 — interval = 6 * (new_count - 1) * EF_factor
            interval_days = max(1, round(6 * new_ef))

    next_review = now + timedelta(days=interval_days)
    return ScheduleResult(
        next_review_at=next_review,
        interval_days=interval_days,
        new_ef=round(new_ef, 3),
        review_count=new_count,
    )


def quality_from_result(is_correct: bool, hint_used: bool = False) -> int:
    """Маппинг результата attempt → quality (0..5).

    q=5: верно с первой попытки
    q=4: верно, но с наводящими вопросами
    q=3: верно с подсказкой
    q=2: неверно, но в правильном направлении
    q=1: неверно
    q=0: совсем не понял
    """
    if is_correct and not hint_used:
        return 5
    if is_correct and hint_used:
        return 3
    return 1
