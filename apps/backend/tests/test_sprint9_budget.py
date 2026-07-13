"""Sprint 9.4: AI-бюджет контроль."""
from __future__ import annotations

import os

import pytest

from app.ai import budget


@pytest.fixture(autouse=True)
def reset_inmem():
    """Сбрасываем in-memory счётчики между тестами."""
    budget._INMEM.clear()
    budget._INMEM_DATE.clear()
    yield
    budget._INMEM.clear()
    budget._INMEM_DATE.clear()


class TestBudgetInMemoryFallback:
    """Без Redis: in-memory счётчики работают."""

    def test_first_call_succeeds(self):
        budget.check_and_increment(user_id=1)
        usage = budget.get_usage(user_id=1)
        assert usage["requests_used"] == 1
        assert usage["requests_limit"] >= 1

    def test_increments_correctly(self):
        for _ in range(5):
            budget.check_and_increment(user_id=1)
        usage = budget.get_usage(user_id=1)
        assert usage["requests_used"] == 5

    def test_budget_exceeded_raises(self, monkeypatch):
        """При превышении лимита — BudgetExceeded."""
        monkeypatch.setattr(budget, "DAILY_REQUESTS_LIMIT", 3)
        # Reset state для monkeypatch
        budget._INMEM.clear()
        budget._INMEM_DATE.clear()

        for _ in range(3):
            budget.check_and_increment(user_id=1)
        with pytest.raises(budget.BudgetExceeded) as exc:
            budget.check_and_increment(user_id=1)
        assert exc.value.limit_kind == "requests"
        assert exc.value.used == 4
        assert exc.value.limit == 3

    def test_separate_users_independent(self):
        """Разные пользователи — разные счётчики."""
        budget.check_and_increment(user_id=1)
        budget.check_and_increment(user_id=1)
        budget.check_and_increment(user_id=2)
        assert budget.get_usage(user_id=1)["requests_used"] == 2
        assert budget.get_usage(user_id=2)["requests_used"] == 1


class TestBudgetResetDay:
    """На границе суток счётчики сбрасываются (in-memory)."""

    def test_new_day_resets_counter(self, monkeypatch):
        # Используем user_id=42, прогоняем звонок в день 1
        monkeypatch.setattr(budget, "_today", lambda: "20260712")
        budget.check_and_increment(user_id=42)
        assert budget.get_usage(user_id=42)["requests_used"] == 1

        # Меняем дату — счётчики сбрасываются
        monkeypatch.setattr(budget, "_today", lambda: "20260713")
        # Доступ к in-memory сначала вызовет cleanup при следующем обращении
        assert budget.get_usage(user_id=42)["requests_used"] == 0


class TestBudgetUsage:
    """get_usage возвращает понятную структуру для UI."""

    def test_get_usage_shape(self):
        budget.check_and_increment(user_id=1)
        usage = budget.get_usage(user_id=1)
        assert "requests_used" in usage
        assert "requests_limit" in usage
        assert "tokens_used" in usage
        assert "tokens_limit" in usage
        assert "alert_threshold_pct" in usage
        assert isinstance(usage["requests_used"], int)
        assert isinstance(usage["alert_threshold_pct"], int)
