"""Sprint 64: Redis cache для subjects/topics/materials.

Cache strategy:
- Read-heavy data (subjects/topics) — cached на 5 мин
- Materials — cached на 2 мин (могут меняться через teacher flow)
- Invalidation: manual (clear_cache) + TTL-based

Используется Redis если доступен, иначе — passthrough.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


# Cache TTL constants
SUBJECTS_TTL = 300  # 5 минут
TOPICS_TTL = 300  # 5 минут
MATERIALS_TTL = 120  # 2 минуты
TOPIC_TTL = 300  # 5 минут


def _get_redis():
    """Sprint 64: lazy import Redis client (graceful если unavailable)."""
    try:
        import redis

        return redis.Redis(host="redis", port=6379, db=0, socket_timeout=2)
    except Exception as e:
        logger.debug(f"Redis unavailable: {e}")
        return None


def cache_get(key: str) -> Optional[Any]:
    """Sprint 64: get cached value (None if miss/error)."""
    r = _get_redis()
    if r is None:
        return None
    try:
        data = r.get(key)
        if data is None:
            return None
        if isinstance(data, bytes):
            data = data.decode("utf-8")
        return json.loads(data)
    except Exception as e:
        logger.debug(f"Cache get failed for {key}: {e}")
        return None


def cache_set(key: str, value: Any, ttl: int) -> bool:
    """Sprint 64: set cached value with TTL."""
    r = _get_redis()
    if r is None:
        return False
    try:
        r.setex(key, ttl, json.dumps(value, default=str))
        return True
    except Exception as e:
        logger.debug(f"Cache set failed for {key}: {e}")
        return False


def cache_invalidate(pattern: str) -> int:
    """Sprint 64: invalidate cache keys matching pattern (для admin operations)."""
    r = _get_redis()
    if r is None:
        return 0
    try:
        keys = list(r.scan_iter(match=pattern))
        if keys:
            return r.delete(*keys)
        return 0
    except Exception as e:
        logger.debug(f"Cache invalidate failed for {pattern}: {e}")
        return 0
