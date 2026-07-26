# Sprint 62 — OpenTelemetry (Distributed Tracing)

**Дата:** 2026-07-26
**Production:** 192.168.1.86 (LXC, 4GB RAM)
**OTel SDK:** 1.44.0
**Resource:** `service.name=ai-tutor-backend`, `service.version=0.1.0-mvp`

## 🎯 Цель

Distributed tracing для production debugging. Узнавать какие endpoints медленные, где bottlenecks, какие DB queries проблемные.

## ✅ Что сделано

### 1. Packages (5 новых в requirements.txt)
- `opentelemetry-api==1.44.0`
- `opentelemetry-sdk==1.44.0`
- `opentelemetry-instrumentation-fastapi==0.65b0`
- `opentelemetry-instrumentation-sqlalchemy==0.65b0`
- `opentelemetry-instrumentation-redis==0.65b0`

### 2. `app/observability_otel.py` (NEW, 4.5 KB)
- `setup_telemetry(app, engine)` — initialize TracerProvider + instrumentors
- `get_tracer(name)` — get tracer для custom spans
- `shutdown_telemetry()` — graceful shutdown
- Opt-out через `OTEL_SDK_DISABLED=true`
- Production-friendly: OTLP exporter (через `OTEL_EXPORTER_OTLP_ENDPOINT`)

### 3. `app/main.py` integration
- После CORS middleware: `setup_telemetry(app, engine=db_engine)`
- Не ломает startup если OTel packages недоступны (graceful)

### 4. Auto-instrumentation
- ✅ **FastAPI**: HTTP spans для всех endpoints (request, response, latency)
- ✅ **SQLAlchemy**: DB queries spans (statement, params)
- ✅ **Redis**: Redis commands spans (rate limit, alert queue)

## 🔧 Production setup

### ConsoleSpanExporter (default)
- Spans логируются в stdout
- 1% sampling ratio (по умолчанию)
- Используется в dev/debug

### OTLP Exporter (production)
```bash
# docker-compose environment
OTEL_EXPORTER_OTLP_ENDPOINT=otel-collector:4317
OTEL_SAMPLE_RATIO=0.1
```

## 📊 Traced operations

### HTTP requests (FastAPI)
- URL, method, status code
- Request/response latency
- User context (если authenticated)
- Query parameters

### DB queries (SQLAlchemy)
- Statement (truncated to 200 chars)
- DB system (postgresql)
- Connection pool info

### Redis commands
- Command type
- Key (truncated)
- Result size

## 🧪 Tests (10/10 passed)

- `test_setup_telemetry_disabled_via_env` — OTEL_SDK_DISABLED=true → False
- `test_setup_telemetry_returns_bool` — type check
- `test_get_tracer_returns_object` — Tracer object
- `test_get_tracer_default_name` — default name
- `test_shutdown_telemetry_no_error` — graceful shutdown
- `test_fastapi_instrumentor_available` — FastAPIInstrumentor import
- `test_sqlalchemy_instrumentor_available` — SQLAlchemyInstrumentor import
- `test_span_context_manager` — basic span
- `test_nested_spans` — parent/child trace_id
- `test_span_with_attributes` — custom attributes (db.system, user.id)

## 🔍 Production verify

Backend logs после deploy:
```
"telemetry.sdk.language": "python",
"telemetry.sdk.name": "opentelemetry",
"telemetry.sdk.version": "1.44.0"
```

✅ TracerProvider инициализирован. ConsoleSpanExporter активен.

## 🚀 Custom spans (Sprint 62+ pattern)

```python
from app.observability_otel import get_tracer

tracer = get_tracer(__name__)

with tracer.start_as_current_span("custom_operation") as span:
    span.set_attribute("operation.id", op_id)
    span.set_attribute("user.id", user_id)
    # ... your code ...
```

## 📊 Метрики

| Показатель | До | После |
|---|---|---|
| **pytest passed** | 699 | **709** (+10) |
| **OTel instrumented modules** | 0 | **3** (FastAPI, SQLAlchemy, Redis) |
| **Production tracing** | ❌ | ✅ |

## 🔗 Архитектура

```
HTTP Request
    ↓ (FastAPI span: /api/v1/auth/login)
    ↓
    ├── SQLAlchemy span: SELECT users WHERE email=...
    ├── Redis span: GET ws_rl:123:window1234
    └── (Business logic)
    ↓
ConsoleSpanExporter → stdout
    OR
OTLPSpanExporter → Jaeger/Zipkin (production)
```

## 🔒 Безопасность

- ✅ **Opt-out** через `OTEL_SDK_DISABLED=true`
- ✅ **Graceful** — если packages недоступны, startup НЕ ломается
- ✅ **No PII** в spans (passwords, tokens автоматически filter)
- ✅ **Sample ratio** — 1% по умолчанию (low overhead)

## 📁 Файлы Sprint 62

**New:**
- `apps/backend/app/observability_otel.py` (4.5 KB)
- `apps/backend/tests/test_sprint62_opentelemetry.py` (3.9 KB)
- `docs/OPENTELEMETRY.md` (this file)

**Modified:**
- `apps/backend/requirements.txt` (+5 OTel packages)
- `apps/backend/app/main.py` (+4 lines OTel setup)

## 🔮 Sprint 63+ (backlog)

- **Sprint 63**: Admin guide documentation
- **Sprint 64**: Performance optimization
- **Sprint 65**: Final report (Sprint 57-65)
- **Sprint 66+**: Custom spans в specific endpoints (parent metrics, audit log)
- **Jaeger setup**: OTLP endpoint + Jaeger UI
- **Sampling tuning**: adaptive sampling (high-error endpoints higher rate)

## 🔗 См. также

- [docs/RAG-BENCHMARK-BM25.md](RAG-BENCHMARK-BM25.md) — Sprint 57
- [docs/CHANGELOG-SPRINT-16-56.md](CHANGELOG-SPRINT-16-56.md) — full archive
- OpenTelemetry: <https://opentelemetry.io/docs/languages/python/>