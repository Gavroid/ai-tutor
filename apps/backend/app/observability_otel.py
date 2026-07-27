"""Sprint 62: OpenTelemetry setup для distributed tracing.

Минимально-инвазивная setup:
- TracerProvider с ConsoleSpanExporter (development) / InMemorySpanExporter (production)
- FastAPIInstrumentor для HTTP spans
- SQLAlchemyInstrumentor для DB queries
- RedisInstrumentor для Redis commands
- Resource attributes (service.name, service.version)

Production-ready: traces могут быть экспортированы в Jaeger/Zipkin
через OTLP exporter (configurable via OTEL_EXPORTER_OTLP_ENDPOINT).
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def setup_telemetry(app=None, engine=None) -> bool:
    """Sprint 62: initialize OpenTelemetry tracing.

    Returns True если setup успешен, False если пакеты недоступны.
    """
    # Sprint 62: env var для opt-out (для tests/debug)
    if os.getenv("OTEL_SDK_DISABLED", "false").lower() == "true":
        logger.info("OpenTelemetry disabled via OTEL_SDK_DISABLED env var")
        return False

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import (
            BatchSpanProcessor,
            ConsoleSpanExporter,
        )
    except ImportError as e:
        logger.warning(f"OpenTelemetry packages not available: {e}")
        return False

    # Resource: service name + version + semantic conventions.
    # Sprint 95: добавлены host.name, process.pid, runtime info
    # (per OTel semantic conventions: https://opentelemetry.io/docs/specs/semconv/)
    import platform
    import socket

    # Get git commit short hash (если доступен)
    commit_sha = "unknown"
    try:
        import subprocess

        commit_sha = (
            subprocess.run(
                ["git", "-C", "/opt/ai-tutor/apps/backend", "rev-parse", "--short", "HEAD"],
                capture_output=True,
                text=True,
                timeout=2,
            ).stdout.strip()
            or "unknown"
        )
    except Exception:
        pass

    resource = Resource.create(
        {
            # Service
            "service.name": "ai-tutor-backend",
            "service.version": "0.1.0-mvp",
            "service.instance.id": socket.gethostname(),
            # Deployment
            "deployment.environment": os.getenv("APP_ENV", "production"),
            "deployment.git.commit_sha": commit_sha,
            # Host
            "host.name": socket.gethostname(),
            "host.arch": platform.machine(),
            # Process
            "process.pid": os.getpid(),
            "process.runtime.name": "python",
            "process.runtime.version": platform.python_version(),
        }
    )

    # TracerProvider
    provider = TracerProvider(resource=resource)

    # Exporter: console (debug) для sample 1%
    # В production можно подключить OTLPExporter для Jaeger/Zipkin
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if otlp_endpoint:
        # Sprint 91: try gRPC exporter first, fallback to HTTP.
        # gRPC требует otlp-proto-grpc, HTTP требует otlp-proto-http.
        # HTTP более firewall-friendly (только HTTPS port 4318).
        exporter_configured = False
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                OTLPSpanExporter as GrpcExporter,
            )
            exporter = GrpcExporter(endpoint=otlp_endpoint, insecure=True)
            provider.add_span_processor(BatchSpanProcessor(exporter))
            logger.info(f"OTLP gRPC exporter configured: {otlp_endpoint}")
            exporter_configured = True
        except ImportError:
            pass

        if not exporter_configured:
            try:
                from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                    OTLPSpanExporter as HttpExporter,
                )
                # HTTP endpoint: replace port if needed
                # gRPC default 4317 → HTTP 4318 (если не указан)
                http_endpoint = otlp_endpoint
                if ":4317" in http_endpoint:
                    http_endpoint = http_endpoint.replace(":4317", ":4318")
                exporter = HttpExporter(endpoint=f"{http_endpoint}/v1/traces")
                provider.add_span_processor(BatchSpanProcessor(exporter))
                logger.info(f"OTLP HTTP exporter configured: {http_endpoint}/v1/traces")
                exporter_configured = True
            except ImportError:
                pass

        if not exporter_configured:
            logger.warning("OTLP exporters not available, falling back to console")
            provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    else:
        # По умолчанию — console exporter (для debugging)
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

    trace.set_tracer_provider(provider)

    # Instrument FastAPI
    if app is not None:
        try:
            from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

            FastAPIInstrumentor.instrument_app(app)
            logger.info("FastAPI instrumented")
        except Exception as e:
            logger.warning(f"Failed to instrument FastAPI: {e}")

    # Instrument SQLAlchemy
    if engine is not None:
        try:
            from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

            SQLAlchemyInstrumentor().instrument(engine=engine)
            logger.info("SQLAlchemy instrumented")
        except Exception as e:
            logger.warning(f"Failed to instrument SQLAlchemy: {e}")

    # Instrument Redis (optional, gracefully skip if not configured)
    try:
        from opentelemetry.instrumentation.redis import RedisInstrumentor

        RedisInstrumentor().instrument()
        logger.info("Redis instrumented")
    except Exception as e:
        logger.debug(f"Redis instrumentation skipped: {e}")

    return True


def get_tracer(name: str = __name__):
    """Sprint 62: get tracer for custom spans."""
    from opentelemetry import trace

    return trace.get_tracer(name)


def shutdown_telemetry():
    """Sprint 62: graceful shutdown — flush all pending spans."""
    try:
        from opentelemetry import trace

        provider = trace.get_tracer_provider()
        # SDK provider has shutdown(); noop/mocked providers don't
        shutdown_fn = getattr(provider, "shutdown", None)
        if callable(shutdown_fn):
            shutdown_fn()
    except Exception as e:
        logger.debug(f"Telemetry shutdown skipped: {e}")
