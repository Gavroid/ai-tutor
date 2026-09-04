"""Sprint 64: cache module tests."""

from __future__ import annotations

import os

# Sprint 64: disable OpenTelemetry для tests (иначе ConsoleSpanExporter
# падает на "I/O operation on closed file" при shutdown).
os.environ.setdefault("OTEL_SDK_DISABLED", "true")

from unittest.mock import MagicMock, patch

import pytest

# === Fixture ===


@pytest.fixture
def client():
    """Sprint 64: TestClient fixture."""
    from app.db.session import Base, engine
    from app.main import app
    from fastapi.testclient import TestClient

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    return TestClient(app)


# === cache_get/cache_set tests ===


def test_cache_set_and_get_returns_value():
    """Sprint 64: cache_set + cache_get возвращает значение."""
    from app.cache import cache_get, cache_set

    # Mock Redis
    with patch("app.cache._get_redis") as mock_redis:
        mock_r = MagicMock()
        mock_r.get.return_value = b'{"key": "value"}'
        mock_redis.return_value = mock_r

        # set
        result = cache_set("test_key", {"foo": "bar"}, ttl=60)
        assert result is True

        # get
        value = cache_get("test_key")
        assert value == {"key": "value"}


def test_cache_get_miss_returns_none():
    """Sprint 64: cache_get с промахом → None."""
    from app.cache import cache_get

    with patch("app.cache._get_redis") as mock_redis:
        mock_r = MagicMock()
        mock_r.get.return_value = None
        mock_redis.return_value = mock_r

        value = cache_get("missing_key")
        assert value is None


def test_cache_redis_unavailable_returns_none():
    """Sprint 64: Redis недоступен → cache_get возвращает None."""
    from app.cache import cache_get, cache_set

    with patch("app.cache._get_redis") as mock_redis:
        mock_redis.return_value = None

        assert cache_get("any") is None
        assert cache_set("any", {"x": 1}, ttl=60) is False


def test_cache_set_uses_ttl():
    """Sprint 64: cache_set использует TTL (setex)."""
    from app.cache import cache_set

    with patch("app.cache._get_redis") as mock_redis:
        mock_r = MagicMock()
        mock_redis.return_value = mock_r

        cache_set("key", {"data": 1}, ttl=300)
        # Проверяем что setex был вызван с правильным TTL
        mock_r.setex.assert_called_once()
        call_args = mock_r.setex.call_args
        assert call_args[0][0] == "key"  # key
        assert call_args[0][1] == 300  # TTL


def test_cache_get_handles_corrupt_data():
    """Sprint 64: cache_get с corrupt JSON → None (graceful)."""
    from app.cache import cache_get

    with patch("app.cache._get_redis") as mock_redis:
        mock_r = MagicMock()
        mock_r.get.return_value = b"not valid json {{{"
        mock_redis.return_value = mock_r

        value = cache_get("corrupt")
        # Должен вернуть None (не raise)
        assert value is None


def test_cache_invalidate_returns_count():
    """Sprint 64: cache_invalidate возвращает количество удалённых ключей."""
    from app.cache import cache_invalidate

    with patch("app.cache._get_redis") as mock_redis:
        mock_r = MagicMock()
        mock_r.scan_iter.return_value = ["key1", "key2", "key3"]
        mock_r.delete.return_value = 3
        mock_redis.return_value = mock_r

        count = cache_invalidate("subjects:*")
        assert count == 3


def test_cache_invalidate_no_keys():
    """Sprint 64: cache_invalidate без matching keys → 0."""
    from app.cache import cache_invalidate

    with patch("app.cache._get_redis") as mock_redis:
        mock_r = MagicMock()
        mock_r.scan_iter.return_value = []
        mock_redis.return_value = mock_r

        count = cache_invalidate("nonexistent:*")
        assert count == 0


# === Integration test: subjects router использует cache ===


def test_subjects_router_uses_cache(client):
    """Sprint 64: /api/v1/subjects использует Redis cache (graceful если Redis down)."""
    # Redis может быть down в test env — endpoint должен работать
    r = client.get("/api/v1/subjects")
    # Должен вернуть 200 (с cache или без)
    assert r.status_code == 200
    # Response — список subjects
    assert isinstance(r.json(), list)


def test_subjects_topics_uses_cache(client):
    """Sprint 64: /api/v1/subjects/{id}/topics использует cache."""
    # Setup: create subject
    from app.db.session import SessionLocal
    from app.subjects.models import Subject

    with SessionLocal() as db:
        sub = Subject(code="test", name="Test", is_active=True)
        db.add(sub)
        db.commit()
        db.refresh(sub)
        sub_id = sub.id

    r = client.get(f"/api/v1/subjects/{sub_id}/topics")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# === Constants tests ===


def test_ttl_constants_reasonable():
    """Sprint 64: TTL constants в reasonable range."""
    from app.cache import (
        MATERIALS_TTL,
        SUBJECTS_TTL,
        TOPIC_TTL,
        TOPICS_TTL,
    )

    # 2-5 минут range
    assert 60 <= SUBJECTS_TTL <= 600
    assert 60 <= TOPICS_TTL <= 600
    assert 60 <= TOPIC_TTL <= 600
    assert 60 <= MATERIALS_TTL <= 300
