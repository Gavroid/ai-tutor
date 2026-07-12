"""Pytest configuration: гарантируем APP_SECRET_KEY и SQLite-in-memory для unit-тестов.

Этап 1 — тестируем только healthcheck, без БД. С PostgreSQL-тестами
перейдём в Этапе 2 (после появления users и миграций).
"""
from __future__ import annotations

import os

# Эти переменные читаются pydantic-settings до создания приложения.
os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-for-pytest-only-1234567890")
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")

# Импортируем ВСЕ модели, чтобы Base.metadata.create_all включал их в SQLite-in-memory.
# Каждый тест начинает с drop_all + create_all на чистой in-memory БД.
from app.db.session import Base  # noqa: E402
from app.users import models as _users_models  # noqa: F401, E402
from app.subjects import models as _subjects_models  # noqa: F401, E402
from app.progress import models as _progress_models  # noqa: F401, E402
from app.diagnostics import models as _diagnostics_models  # noqa: F401, E402
from app.admin import models as _admin_models  # noqa: F401, E402
from app.notifications import models as _notifications_models  # noqa: F401, E402
from app.auth import password_reset_models as _password_reset_models  # noqa: F401, E402

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_state():
    """Очищаем глобальный state перед/после каждого теста.

    Без этого:
    - test_login_rate_limit оставит _login_attempts_log заполненным
    - test_ws_rate_limit оставит _ws_concurrent_log заполненным
    - test_ai оставит _ai_call_log заполненным
    - любой TestClient может оставить dependency_overrides, и следующий
      тест получит чужой session
    - pydantic-settings кэширует get_settings() — нужно сбрасывать кэш
      перед каждым тестом, чтобы UPLOAD_DIR/AI_* обновлялись корректно
    """
    from app.config import get_settings
    from app.main import (
        _login_attempts_log,
        _register_attempts_log,
        _ws_concurrent_log,
        _ai_call_log,
        app,
    )

    get_settings.cache_clear()
    _login_attempts_log.clear()
    _register_attempts_log.clear()
    _ws_concurrent_log.clear()
    _ai_call_log.clear()
    app.dependency_overrides.clear()
    yield
    get_settings.cache_clear()
    _login_attempts_log.clear()
    _register_attempts_log.clear()
    _ws_concurrent_log.clear()
    _ai_call_log.clear()
    app.dependency_overrides.clear()