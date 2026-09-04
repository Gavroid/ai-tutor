"""Sprint 49: Parent metrics для Grafana dashboards.

Custom Prometheus metrics для parent-dashboard.json (Sprint 39).
Безопасно: только timing-based counters, НЕ glucose data.
"""
from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

# Sprint 49: parent_streak_* (gauge per user).
parent_streak_current_streak_days = Gauge(
    "parent_streak_current_streak_days",
    "Current streak days (T1D-friendly, no 'STREAK LOST' pressure)",
    ["user_id"],
)

parent_streak_longest_streak_days = Gauge(
    "parent_streak_longest_streak_days",
    "Longest streak days for the user",
    ["user_id"],
)

# Sprint 49: parent_subject_mastery_avg (gauge per subject).
parent_subject_mastery_avg = Gauge(
    "parent_subject_mastery_avg",
    "Average mastery score by subject (0.0 to 1.0)",
    ["user_id", "subject"],
)

# Sprint 49: parent_attempts_total (counter per user/day).
parent_attempts_total = Counter(
    "parent_attempts_total",
    "Total attempts by user (daily counter, label: day YYYY-MM-DD)",
    ["user_id", "day"],
)

# Sprint 49: parent_session_pauses_total (counter per reason).
parent_session_pauses_total = Counter(
    "parent_session_pauses_total",
    "T1D session pauses by reason (break/hypo/hyper/other)",
    ["user_id", "reason"],
)

# Sprint 49: parent_session_duration_seconds (histogram).
parent_session_duration_seconds = Histogram(
    "parent_session_duration_seconds",
    "Session duration in seconds (T1D safety: >40min → red flag)",
    buckets=(60, 300, 600, 1200, 1800, 2400, 3600, 7200),
)


def set_streak_metrics(user_id: int, current: int, longest: int) -> None:
    """Sprint 49: update streak gauges."""
    parent_streak_current_streak_days.labels(user_id=str(user_id)).set(current)
    parent_streak_longest_streak_days.labels(user_id=str(user_id)).set(longest)


def set_subject_mastery(user_id: int, subject: str, mastery: float) -> None:
    """Sprint 49: update subject mastery gauge."""
    parent_subject_mastery_avg.labels(user_id=str(user_id), subject=subject).set(mastery)


def increment_attempt(user_id: int, day: str) -> None:
    """Sprint 49: increment attempt counter."""
    parent_attempts_total.labels(user_id=str(user_id), day=day).inc()


def increment_pause(user_id: int, reason: str) -> None:
    """Sprint 49: increment pause counter."""
    parent_session_pauses_total.labels(user_id=str(user_id), reason=reason).inc()


def observe_session_duration(duration_seconds: float) -> None:
    """Sprint 49: observe session duration."""
    parent_session_duration_seconds.observe(duration_seconds)
