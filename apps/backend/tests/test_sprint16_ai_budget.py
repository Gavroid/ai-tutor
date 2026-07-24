"""Sprint 16.1 P1-3: AI budget enforcement на WebSocket.

WebSocket chat должен проверять budget так же как HTTP endpoints,
иначе user может обойти лимит через прямой WS.
"""
from __future__ import annotations

import os

os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-for-pytest-only-1234567890")
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")
os.environ.setdefault("AI_API_KEY", "mock-key-for-tests")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "mock-token")

import pytest

from app.ai import budget
from app.users.models import User, Role
from app.auth.security import hash_password
from app.auth.security import create_access_token
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def db_session():
    """In-memory SQLite с users таблицей."""
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                display_name VARCHAR(255) NOT NULL DEFAULT '',
                role VARCHAR(20) NOT NULL DEFAULT 'student',
                is_active BOOLEAN NOT NULL DEFAULT 1
            )
        """))
        conn.execute(text(
            "INSERT INTO users (email, password_hash, display_name, role, is_active) "
            "VALUES (:e, :p, 'Test', 'student', 1)"
        ), {"e": "test@example.com", "p": hash_password("testpass1")})
    return engine


@pytest.fixture
def fresh_budget():
    """Reset budget in-memory state для каждого теста."""
    # save original limits
    orig_req = budget.DAILY_REQUESTS_LIMIT
    orig_tok = budget.DAILY_TOKENS_LIMIT
    # set small limit для теста
    budget.DAILY_REQUESTS_LIMIT = 2
    budget.DAILY_TOKENS_LIMIT = 100
    # clear in-memory state
    budget._INMEM.clear()
    budget._INMEM_DATE.clear()
    yield
    # restore
    budget.DAILY_REQUESTS_LIMIT = orig_req
    budget.DAILY_TOKENS_LIMIT = orig_tok
    budget._INMEM.clear()
    budget._INMEM_DATE.clear()


def test_budget_check_and_increment_under_limit(fresh_budget):
    """Под лимитом — OK."""
    for i in range(2):
        budget.check_and_increment(user_id=42)  # не должно raise


def test_budget_check_and_increment_over_limit(fresh_budget):
    """Превышение → BudgetExceeded."""
    from app.ai.budget import BudgetExceeded

    budget.check_and_increment(user_id=42)
    budget.check_and_increment(user_id=42)

    with pytest.raises(BudgetExceeded) as exc_info:
        budget.check_and_increment(user_id=42)

    assert exc_info.value.limit_kind == "requests"
    assert exc_info.value.used == 3
    assert exc_info.value.limit == 2


def test_budget_separate_users_independent(fresh_budget):
    """Разные пользователи — независимые счётчики."""
    from app.ai.budget import BudgetExceeded

    # user 1 использует все свои
    budget.check_and_increment(user_id=1)
    budget.check_and_increment(user_id=1)

    with pytest.raises(BudgetExceeded):
        budget.check_and_increment(user_id=1)

    # user 2 — может
    budget.check_and_increment(user_id=2)
    budget.check_and_increment(user_id=2)


def test_budget_get_usage(fresh_budget):
    """get_usage возвращает used/limit/alert_threshold."""
    budget.check_and_increment(user_id=42)
    usage = budget.get_usage(42)
    assert usage["requests_used"] == 1
    assert usage["requests_limit"] == 2
    assert usage["tokens_used"] == 0
    assert usage["alert_threshold_pct"] == 80