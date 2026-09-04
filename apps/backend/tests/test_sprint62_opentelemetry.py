"""Sprint 62: OpenTelemetry tests."""
from __future__ import annotations

import os

# Sprint 64: tests которым нужен real OTel — unset OTEL_SDK_DISABLED
# (conftest ставит его чтобы ConsoleSpanExporter не падал в других тестах)
os.environ["OTEL_SDK_DISABLED"] = "false"

from unittest.mock import patch

import pytest

# === setup_telemetry() tests ===

def test_setup_telemetry_disabled_via_env(monkeypatch):
    """Sprint 62: OTEL_SDK_DISABLED=true → setup returns False."""
    from app.observability_otel import setup_telemetry

    monkeypatch.setenv("OTEL_SDK_DISABLED", "true")
    result = setup_telemetry()
    assert result is False


def test_setup_telemetry_returns_bool():
    """Sprint 62: setup_telemetry returns bool (True if enabled, False if not)."""
    from app.observability_otel import setup_telemetry

    result = setup_telemetry()
    # Может быть True или False в зависимости от наличия пакетов
    assert isinstance(result, bool)


def test_get_tracer_returns_object():
    """Sprint 62: get_tracer возвращает Tracer object."""
    from app.observability_otel import get_tracer

    tracer = get_tracer("test_module")
    assert tracer is not None
    # Tracer имеет .start_as_current_span
    assert hasattr(tracer, "start_as_current_span")


def test_get_tracer_default_name():
    """Sprint 62: get_tracer без args → default name."""
    from app.observability_otel import get_tracer

    tracer = get_tracer()
    assert tracer is not None


def test_shutdown_telemetry_no_error():
    """Sprint 62: shutdown_telemetry не падает (даже без setup)."""
    from app.observability_otel import shutdown_telemetry

    # Должен не raise (либо shutdown либо noop)
    shutdown_telemetry()


# === Integration: FastAPI spans ===

def test_fastapi_instrumentor_available():
    """Sprint 62: FastAPIInstrumentor available (или skip если нет)."""
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        assert FastAPIInstrumentor is not None
    except ImportError:
        pytest.skip("FastAPI instrumentation not available")


def test_sqlalchemy_instrumentor_available():
    """Sprint 62: SQLAlchemyInstrumentor available."""
    try:
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
        assert SQLAlchemyInstrumentor is not None
    except ImportError:
        pytest.skip("SQLAlchemy instrumentation not available")


# === Real-world: trace context propagation ===

def test_span_context_manager():
    """Sprint 62: создание span через context manager."""
    from opentelemetry.sdk.trace import TracerProvider

    # Sprint 64: используем direct provider (set_tracer_provider не работает
    # если OTEL_SDK_DISABLED=true → SDK отключает провайдер)
    provider = TracerProvider()
    tracer = provider.get_tracer("test")
    with tracer.start_as_current_span("test_operation") as span:
        # Span имеет trace_id и span_id
        ctx = span.get_span_context()
        assert ctx.trace_id != 0
        assert ctx.span_id != 0


def test_nested_spans():
    """Sprint 62: nested spans share trace_id."""
    from opentelemetry.sdk.trace import TracerProvider

    provider = TracerProvider()
    tracer = provider.get_tracer("test")
    with tracer.start_as_current_span("parent") as parent_span:
        parent_trace_id = parent_span.get_span_context().trace_id

        with tracer.start_as_current_span("child") as child_span:
            child_trace_id = child_span.get_span_context().trace_id
            # Child shares trace_id с parent
            assert child_trace_id == parent_trace_id


def test_span_with_attributes():
    """Sprint 62: span с attributes (для production debugging)."""
    from opentelemetry.sdk.trace import TracerProvider

    provider = TracerProvider()
    tracer = provider.get_tracer("test")
    with tracer.start_as_current_span("db_query") as span:
        span.set_attribute("db.system", "postgresql")
        span.set_attribute("db.statement", "SELECT * FROM users")
        span.set_attribute("user.id", 123)
        # Проверяем что атрибуты установлены
        # (не падают)
        ctx = span.get_span_context()
        assert ctx.span_id != 0
