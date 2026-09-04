"""Sprint 80: AI budget hourly limit tests (burst protection)."""
from __future__ import annotations

import os

os.environ.setdefault("OTEL_SDK_DISABLED", "true")

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# === Module tests ===

def test_hourly_limit_constant_defined():
    """Sprint 80: HOURLY_REQUESTS_LIMIT defined."""
    from app.ai import budget as budget_module

    assert hasattr(budget_module, "HOURLY_REQUESTS_LIMIT")
    assert budget_module.HOURLY_REQUESTS_LIMIT >= 1
    assert budget_module.HOURLY_REQUESTS_LIMIT <= 100  # reasonable burst limit


def test_check_and_increment_uses_hourly():
    """Sprint 80: check_and_increment использует hourly_req key."""
    # Verify source code has hourly_req key
    with open(
        os.path.join(
            os.path.dirname(__file__),
            "..", "app", "ai", "budget.py",
        )
    ) as f:
        content = f.read()
    assert "hourly_req" in content, "Sprint 80: hourly_req key должен быть"
    assert "HOURLY_REQUESTS_LIMIT" in content
    assert "hourly_requests" in content, "Sprint 80: hourly_requests category"


def test_budget_exceeded_supports_hourly_requests():
    """Sprint 80: BudgetExceeded принимает hourly_requests kind."""
    from app.ai.budget import BudgetExceeded

    exc = BudgetExceeded("hourly_requests", 25, 20)
    assert exc.limit_kind == "hourly_requests"
    assert exc.used == 25
    assert exc.limit == 20
    assert "hourly_requests" in str(exc)


def test_get_usage_includes_hourly():
    """Sprint 80: get_usage возвращает hourly fields."""
    # Verify source has hourly fields
    import inspect

    from app.ai import budget as budget_module
    source = inspect.getsource(budget_module.get_usage)
    assert "hourly_used" in source
    assert "hourly_limit" in source


# === Mock integration tests ===

@pytest.mark.asyncio
async def test_hourly_limit_raises_budget_exceeded(monkeypatch):
    """Sprint 80: > HOURLY_REQUESTS_LIMIT req/hour → BudgetExceeded.

    Sprint 3.9.5: default HOURLY_REQUESTS_LIMIT=60 (Кирилл попросил). Тест
    использует 70 как значение больше default, чтобы не зависеть от env override.
    """
    from app.ai import budget as budget_module

    # Mock _increment чтобы always возвращать > limit
    counter = [0]

    def mock_increment(key, limit, ttl, by=1):
        counter[0] += 1
        return 70  # больше HOURLY_REQUESTS_LIMIT (default 60 после Sprint 3.9.5)

    monkeypatch.setattr(budget_module, "_increment", mock_increment)
    monkeypatch.setattr(budget_module, "_try_redis", lambda: None)

    with pytest.raises(budget_module.BudgetExceeded) as exc:
        budget_module.check_and_increment(user_id=42)

    assert exc.value.limit_kind == "hourly_requests"
    assert exc.value.used == 70


def test_hourly_limit_default_value():
    """Sprint 80 + 3.9.5: HOURLY_REQUESTS_LIMIT по умолчанию 60 (Кирилл попросил больше).

    Первоначальный default был 20; Sprint 3.9.5 расширил до 60 по запросу пользователя
    (см. app/ai/budget.py:28-29). Тест отражает актуальный дефолт.
    """
    import os
    # Remove env var to test default
    old = os.environ.pop("AI_BUDGET_REQUESTS_PER_HOUR", None)
    try:
        # Re-import to get fresh default
        import importlib

        from app.ai import budget as budget_module
        importlib.reload(budget_module)

        # Sprint 3.9.5: default = 60 (Кирилл попросил), см. app/ai/budget.py:29.
        assert budget_module.HOURLY_REQUESTS_LIMIT == 60
    finally:
        if old is not None:
            os.environ["AI_BUDGET_REQUESTS_PER_HOUR"] = old
