"""AI-budget контроль (Sprint 9.4).

Ограничивает:
- Количество AI-вызовов на пользователя в день.
- Суммарное количество выходных токенов на пользователя в день.

Хранилище — Redis (multi-worker safe).
Fallback на in-memory dict, если Redis недоступен.

TODO (Sprint 9.4+):
- Алерт в Telegram при превышении `alert_threshold_pct` от дневного лимита.
- UI в /admin для настройки лимитов по mode.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Лимиты по умолчанию (на пользователя в день).
# Можно переопределить через env: AI_BUDGET_REQUESTS_PER_DAY, AI_BUDGET_TOKENS_PER_DAY.
# Sprint 3.9.5: Кирилл попросил 250 req / 500k токенов.
DAILY_REQUESTS_LIMIT = int(os.environ.get("AI_BUDGET_REQUESTS_PER_DAY", "250"))
DAILY_TOKENS_LIMIT = int(os.environ.get("AI_BUDGET_TOKENS_PER_DAY", "500000"))
# Sprint 80: hourly limit — burst protection (24h limit не защищает от burst).
# Sprint 3.9.5: Кирилл попросил 60/час вместо 20/час.
HOURLY_REQUESTS_LIMIT = int(os.environ.get("AI_BUDGET_REQUESTS_PER_HOUR", "60"))
ALERT_THRESHOLD_PCT = int(os.environ.get("AI_BUDGET_ALERT_PCT", "80"))


# Sprint 86: hot-reload поддержка.
# Module-level constants могут быть переопределены через reload_limits()
# БЕЗ рестарта backend (для admin ops).
def reload_limits(
    daily_requests: int | None = None,
    daily_tokens: int | None = None,
    hourly_requests: int | None = None,
    alert_threshold: int | None = None,
) -> None:
    """Sprint 86: runtime reload AI budget limits.

    Безопасные изменения (не требуют рестарта):
    - Daily requests limit
    - Daily tokens limit
    - Hourly requests limit (burst)
    - Alert threshold %

    Args:
        daily_requests: новый DAILY_REQUESTS_LIMIT (None = keep current)
        daily_tokens: новый DAILY_TOKENS_LIMIT
        hourly_requests: новый HOURLY_REQUESTS_LIMIT
        alert_threshold: новый ALERT_THRESHOLD_PCT
    """
    global DAILY_REQUESTS_LIMIT, DAILY_TOKENS_LIMIT, HOURLY_REQUESTS_LIMIT, ALERT_THRESHOLD_PCT
    if daily_requests is not None:
        if daily_requests < 1:
            raise ValueError(f"daily_requests must be >=1, got {daily_requests}")
        DAILY_REQUESTS_LIMIT = daily_requests
    if daily_tokens is not None:
        if daily_tokens < 100:
            raise ValueError(f"daily_tokens must be >=100, got {daily_tokens}")
        DAILY_TOKENS_LIMIT = daily_tokens
    if hourly_requests is not None:
        if hourly_requests < 1 or hourly_requests > DAILY_REQUESTS_LIMIT:
            raise ValueError(
                f"hourly_requests must be 1-{DAILY_REQUESTS_LIMIT}, got {hourly_requests}"
            )
        HOURLY_REQUESTS_LIMIT = hourly_requests
    if alert_threshold is not None:
        if alert_threshold < 1 or alert_threshold > 100:
            raise ValueError(f"alert_threshold must be 1-100, got {alert_threshold}")
        ALERT_THRESHOLD_PCT = alert_threshold
    logger.info(
        "AI budget limits reloaded: daily_req=%s daily_tok=%s hourly_req=%s alert_pct=%s",
        DAILY_REQUESTS_LIMIT, DAILY_TOKENS_LIMIT, HOURLY_REQUESTS_LIMIT, ALERT_THRESHOLD_PCT,
    )


def _try_redis():
    try:
        import redis
        url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
        r = redis.Redis.from_url(url, decode_responses=True)
        if r.ping():
            return r
    except Exception:
        return None
    return None


_REDIS = _try_redis()
_INMEM: dict[int, dict[str, int]] = {}
_INMEM_DATE: dict[int, str] = {}


def reset_budget_state() -> None:
    """Sprint 4 (testing): сбросить in-memory budget dict между тестами.

    Продакшн НЕ использует _INMEM (только если Redis недоступен).
    Тесты с parametrize (15 topics × multi-call) могут исчерпать per-user
    budget между модулями, поэтому fixture явно сбрасывает.
    """
    _INMEM.clear()
    _INMEM_DATE.clear()


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d")


def _key(user_id: int, kind: str) -> str:
    return f"ai-budget:{_today()}:{kind}:{user_id}"


class BudgetExceeded(Exception):
    """Исключение: AI-бюджет пользователя на сегодня исчерпан."""

    def __init__(self, limit_kind: str, used: int, limit: int):
        super().__init__(f"AI {limit_kind} budget exceeded: {used}/{limit}")
        self.limit_kind = limit_kind
        self.used = used
        self.limit = limit


def check_and_increment(user_id: int, *, estimated_output_tokens: int = 0) -> None:
    """Проверить и инкрементировать счётчик использования AI для пользователя.

    Raises:
        BudgetExceeded: если превышен дневной лимит.
    """
    # Sprint 80: hourly limit (burst protection)
    # Используем отдельный ключ с TTL 3600 (1 час).
    hourly_used = _increment(_key(user_id, "hourly_req"), HOURLY_REQUESTS_LIMIT, ttl=3600)
    if hourly_used > HOURLY_REQUESTS_LIMIT:
        raise BudgetExceeded("hourly_requests", hourly_used, HOURLY_REQUESTS_LIMIT)

    # 1) Счётчик запросов
    requests_used = _increment(_key(user_id, "req"), DAILY_REQUESTS_LIMIT, ttl=86400)
    if requests_used > DAILY_REQUESTS_LIMIT:
        # Откатим (best-effort): на этом шаге уже поздно — просто raise.
        raise BudgetExceeded("requests", requests_used, DAILY_REQUESTS_LIMIT)

    # 2) Счётчик токенов
    tokens_used = _increment(_key(user_id, "tok"), DAILY_TOKENS_LIMIT, ttl=86400, by=estimated_output_tokens)
    if tokens_used > DAILY_TOKENS_LIMIT:
        raise BudgetExceeded("tokens", tokens_used, DAILY_TOKENS_LIMIT)


def get_usage(user_id: int) -> dict[str, int]:
    """Текущее использование (для UI в /admin/budget)."""
    req = _get(_key(user_id, "req"))
    tok = _get(_key(user_id, "tok"))
    hourly_req = _get(_key(user_id, "hourly_req"))
    return {
        "requests_used": req,
        "requests_limit": DAILY_REQUESTS_LIMIT,
        "hourly_used": hourly_req,
        "hourly_limit": HOURLY_REQUESTS_LIMIT,
        "tokens_used": tok,
        "tokens_limit": DAILY_TOKENS_LIMIT,
        "alert_threshold_pct": ALERT_THRESHOLD_PCT,
    }


def _increment(key: str, limit: int, ttl: int, by: int = 1) -> int:
    """Инкремент counter; если Redis недоступен — in-memory fallback."""
    if _REDIS is not None:
        try:
            pipe = _REDIS.pipeline()
            pipe.incrby(key, by)
            pipe.expire(key, ttl)
            val, _ = pipe.execute()
            return int(val)
        except Exception as e:
            logger.warning("Redis budget incr failed: %s; fallback in-memory", e)
    # in-memory fallback (per-process, неточный в multi-worker)
    _cleanup_inmem_if_new_day()
    bucket = _INMEM.setdefault(_hash_key(key), {})
    bucket[key] = bucket.get(key, 0) + by
    return bucket[key]


def _get(key: str) -> int:
    if _REDIS is not None:
        try:
            v = _REDIS.get(key)
            return int(v) if v is not None else 0
        except Exception:
            pass
    _cleanup_inmem_if_new_day()
    bucket = _INMEM.get(_hash_key(key), {})
    return int(bucket.get(key, 0))


def _hash_key(key: str) -> int:
    """Хэш для группировки in-memory ключей в один bucket по пользователю."""
    # Берём user_id (последний компонент ключа)
    try:
        return int(key.split(":")[-1])
    except (ValueError, IndexError):
        return 0


def _cleanup_inmem_if_new_day() -> None:
    """Сброс in-memory счётчиков при смене дня."""
    today = _today()
    if not hasattr(_cleanup_inmem_if_new_day, "_last"):
        _cleanup_inmem_if_new_day._last = today  # type: ignore
    if _cleanup_inmem_if_new_day._last != today:  # type: ignore
        _INMEM.clear()
        _INMEM_DATE.clear()
        _cleanup_inmem_if_new_day._last = today  # type: ignore
