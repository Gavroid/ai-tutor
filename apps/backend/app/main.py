"""Главный модуль FastAPI-приложения.

Каркас Этапа 1: healthcheck + OpenAPI + базовая структура роутеров.
Авторизация, учебные модули и AI будут подключаться в следующих этапах.
"""
from contextlib import asynccontextmanager
import logging
import os
import time as _time
from typing import AsyncIterator

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db.session import engine

# Sprint 16.1 P1-4: structured logger для access_log middleware.
_access_logger = logging.getLogger("ai_tutor.access")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Startup/shutdown: пингуем БД. Полноценные миграции запускаются отдельно (alembic upgrade head)."""
    from sqlalchemy import text

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 — health-check должен логировать, не падать
        # Sprint 16.1 P1-4: logger вместо print для структурированных логов.
        # На старте БД может быть ещё не готова (race в docker-compose);
        # healthcheck эндпоинт отразит реальное состояние.
        logger.warning("startup DB ping failed: %r", exc)
    yield
    engine.dispose()


def create_app() -> FastAPI:
    import time as _t
    from datetime import datetime as _dt, timezone as _tz

    settings = get_settings()
    app_start_time = _t.time()
    app_started_iso = _dt.now(_tz.utc).isoformat()

    # Делаем доступным для health endpoint
    global _app_start_time, _app_started_iso
    _app_start_time = app_start_time
    _app_started_iso = app_started_iso

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0-mvp",
        description=(
            "AI-репетитор для школьной программы 7 класса (MVP). "
            "T1D-friendly: PauseButton, SessionTimer 3-tier (20/40/60 мин), "
            "audio cue, streak timezone (Europe/Moscow). "
            "Parent 2FA TOTP (8 backup codes). Cookie-based auth (httpOnly). "
            "Multi-worker uvicorn. Telegram alerts при 5xx. "
            "Документация автоматически генерируется из OpenAPI schema.\n\n"
            "**Quick links:**\n"
            "- `/openapi.json` — JSON schema (machine-readable)\n"
            "- `/docs` — Swagger UI (try endpoints)\n"
            "- `/health` — liveness probe (без auth)\n"
            "- `/ready` — readiness probe (БД ping)\n"
        ),
        openapi_tags=[
            {"name": "auth", "description": "Sprint 10.1 + 27. Регистрация, login, refresh, logout, /me. httpOnly cookies."},
            {"name": "teacher", "description": "Sprint 35. Генерация, список (с search), bulk approve материалов. Только teacher/admin."},
            {"name": "parent", "description": "Sprint 32. Приглашения, дашборд ребёнка, 2FA TOTP endpoints."},
            {"name": "students", "description": "Профиль ученика, привязка к parent."},
            {"name": "sessions", "description": "Sprint 34. T1D-friendly session pauses (break/hypo/hyper/other). Streak НЕ ломается."},
            {"name": "ai", "description": "Sprint 25. Генерация ответов AI, check-answer, hint-metrics, budget/usage."},
            {"name": "voice", "description": "Sprint 16.1. Whisper ASR endpoint (async, proper HTTP codes)."},
            {"name": "cgm", "description": "Sprint 40. Nightscout CGM opt-in прокси (HTTPS-only, SSRF protection, БЕЗ сохранения glucose в БД)."},
            {"name": "progress", "description": "Sprint 8.2 + 16.2. Streak, recommend-next (T1D-friendly), progress tracking."},
            {"name": "admin", "description": "Sprint 9.2 + 10.4. Stats, audit-log (с entity filter), kill switch."},
            {"name": "meta", "description": "Healthchecks, version."},
        ],
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        debug=settings.app_debug,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Healthcheck — НЕ авторизуется, не трогает БД.
    @app.get("/health", tags=["meta"], summary="Liveness probe")
    def health() -> dict:
        import time as _t

        return {
            "status": "ok",
            "service": settings.app_name,
            "env": settings.app_env,
            "version": app.version,
            "uptime_seconds": int(_t.time() - _app_start_time),
            "started_at": _app_started_iso,
        }

    # Эндпоинт /ready не считается в rate limit — это healthcheck
    @app.get("/ready", tags=["meta"], summary="Readiness probe (БД доступна)")
    def ready() -> dict[str, str]:
        from sqlalchemy import text

        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        except Exception:  # noqa: BLE001
            # Stage 2 B.1: full exception (potentially contains DB host/credentials/error
            # details) goes only to logs. HTTP body is intentionally generic so we never
            # leak SQL state into a public healthcheck response.
            logging.getLogger(__name__).exception("/ready DB check failed")
            return {"status": "not_ready", "reason": "db_unavailable"}
        return {"status": "ready"}

    # Простой in-memory rate limit для /api/v1/ai/* — защита от спама.
    # В production с несколькими воркерами uvicorn включается Redis через REDIS_URL.
    @app.middleware("http")
    async def rate_limit_ai(request, call_next):
        # === Sprint 4.1: Rate limit для REGISTER (anti-abuse) ===
        if request.url.path == "/api/v1/auth/register" and request.method == "POST":
            from fastapi.responses import JSONResponse

            ip = _client_ip(request, settings.trusted_proxies_list)
            now = _time.time()
            window = 60 * 60.0  # 1 час
            max_attempts = settings.rate_limit_register_per_hour

            redis = _get_redis()
            allowed = True
            if redis is not None:
                try:
                    key = f"register_rl:{ip}:{int(now // window)}"
                    count = await redis.incr(key)
                    if count == 1:
                        await redis.expire(key, int(window) + 1)
                    allowed = count <= max_attempts
                except Exception:
                    allowed = True
            else:
                log = _register_attempts_log.setdefault(ip, [])
                while log and log[0] < now - window:
                    log.pop(0)
                if len(log) >= max_attempts:
                    allowed = False
                else:
                    log.append(now)

            if not allowed:
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Слишком много регистраций с этого IP. Подождите 1 час."
                    },
                )
            return await call_next(request)

        # === Rate limit для LOGIN (anti-bruteforce) ===
        if request.url.path == "/api/v1/auth/login" and request.method == "POST":
            from fastapi.responses import JSONResponse

            ip = _client_ip(request, settings.trusted_proxies_list)
            now = _time.time()
            # 15 минут / 10 попыток на IP
            window = 15 * 60.0
            max_attempts = settings.rate_limit_login_per_15min
            redis = _get_redis()
            allowed = True
            if redis is not None:
                try:
                    key = f"login_rl:{ip}:{int(now // window)}"
                    count = await redis.incr(key)
                    if count == 1:
                        await redis.expire(key, int(window) + 1)
                    allowed = count <= max_attempts
                except Exception:
                    allowed = True
            else:
                log = _login_attempts_log.setdefault(ip, [])
                while log and log[0] < now - window:
                    log.pop(0)
                if len(log) >= max_attempts:
                    allowed = False
                else:
                    log.append(now)

            if not allowed:
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Слишком много попыток входа. Подождите 15 минут."
                    },
                )
            return await call_next(request)

        # === Rate limit для AI endpoints ===
        if request.url.path.startswith("/api/v1/ai/"):
            from app.auth.security import decode_token
            from fastapi import HTTPException
            from jose import JWTError

            # Берём user_id из токена (если есть)
            auth = request.headers.get("authorization", "")
            if auth.startswith("Bearer "):
                try:
                    payload = decode_token(auth[7:])
                    uid = int(payload.get("sub", 0))
                except (JWTError, HTTPException, ValueError):
                    uid = 0
            else:
                uid = 0

            now = _time.time()
            window = 60.0
            from app.config import get_settings
            _ai_settings = get_settings()  # Sprint 3.6.3: local var, не теньет outer settings
            max_calls = _ai_settings.rate_limit_ai_per_minute

            # Sprint 3.6.3: kill switch — emergency stop AI для user.
            # Persistent через Redis (multi-worker safe).
            # Fallback на env если Redis недоступен.
            kill_switch_ids: set[int] = set()
            try:
                redis_client = _get_redis()
                if redis_client is not None:
                    raw = await redis_client.get("ai:kill_switch")
                    # Sprint 3.6.3: _get_redis() использует decode_responses=True,
                    # так что raw — это str, не bytes.
                    if raw:
                        if isinstance(raw, bytes):
                            raw = raw.decode()
                        kill_switch_ids = {int(x) for x in raw if x.isdigit()}
            except Exception:
                # Fallback на env (для boot или Redis unavailable)
                kill_switch_ids = _ai_settings.ai_kill_switch_user_id_set

            if uid in kill_switch_ids:
                from fastapi.responses import JSONResponse
                return JSONResponse(
                    status_code=503,
                    content={
                        "detail": "AI временно недоступен для этого аккаунта. Свяжитесь с родителем или администратором."
                    },
                )

            # Пробуем Redis, fallback на in-memory
            redis = _get_redis()
            allowed = True
            if redis is not None:
                try:
                    key = f"ai_rl:{uid}:{int(now // window)}"
                    count = await redis.incr(key)
                    if count == 1:
                        await redis.expire(key, int(window) + 1)
                    allowed = count <= max_calls
                except Exception:
                    allowed = True  # если Redis сломался — пропускаем
            else:
                log = _ai_call_log.setdefault(uid, [])
                while log and log[0] < now - window:
                    log.pop(0)
                if len(log) >= max_calls:
                    allowed = False
                else:
                    log.append(now)

            if not allowed:
                from fastapi.responses import JSONResponse

                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": f"Превышен лимит AI-запросов ({max_calls}/мин). Подождите немного."
                    },
                )

        # === Rate limit для WebSocket AI endpoints ===
        if request.url.path.startswith("/ws/ai/"):
            # Лимит: 5 одновременных WS-соединений на пользователя (anti-flood/multi-tab)
            try:
                from urllib.parse import parse_qs

                qs = parse_qs(request.url.query)
                toks = qs.get("token", [])
                if toks:
                    from app.auth.security import decode_token

                    try:
                        claim = decode_token(toks[0])
                        uid = int(claim.get("sub", 0))
                    except Exception:
                        uid = 0
                else:
                    uid = 0
            except Exception:
                uid = 0

            if uid > 0:
                now = _time.time()
                window = 60.0
                max_ws = 5
                # Sprint 16.1 P1-1: используем Redis (multi-worker safe)
                # вместо in-memory dict.
                redis = _get_redis()
                allowed = True
                if redis is not None:
                    try:
                        key = f"ws_rl:{uid}:{int(now // window)}"
                        count = await redis.incr(key)
                        if count == 1:
                            await redis.expire(key, int(window) + 1)
                        allowed = count <= max_ws
                    except Exception:
                        allowed = True  # fallback: разрешить если Redis сломался
                else:
                    log = _ws_concurrent_log.setdefault(uid, [])
                    while log and log[0] < now - window:
                        log.pop(0)
                    allowed = len(log) < max_ws
                    if allowed:
                        log.append(now)

                if not allowed:
                    from fastapi.responses import JSONResponse

                    return JSONResponse(
                        status_code=429,
                        content={
                            "detail": f"Слишком много WS-соединений ({max_ws}/мин). Закройте лишние вкладки.",
                        },
                    )

        return await call_next(request)

    @app.middleware("http")
    async def access_log(request, call_next):
        """Structured JSON access log для каждого запроса.

        Включает: method, path, status, duration_ms, ip, user_agent, request_id.
        Пишется в stdout (Docker → /var/lib/docker/containers/*/*.log).
        """
        import json as _json
        import time as _time
        import uuid as _uuid

        request_id = request.headers.get("x-request-id") or _uuid.uuid4().hex[:16]
        start = _time.time()

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = int((_time.time() - start) * 1000)
            entry = {
                "ts": _time.time(),
                "level": "ERROR",
                "method": request.method,
                "path": request.url.path,
                "status": 500,
                "duration_ms": duration_ms,
                "ip": request.client.host if request.client else "unknown",
                "user_agent": request.headers.get("user-agent", ""),
                "request_id": request_id,
                "error": "unhandled",
            }
            # Sprint 16.1 P1-4: print → logger (structured через extra=...)
            _access_logger.error(
                "unhandled_exception",
                extra=entry,
            )
            raise

        duration_ms = int((_time.time() - start) * 1000)

        # Логируем только API и ошибки (404 на /manifest.json это шум)
        if request.url.path.startswith("/api/") or response.status_code >= 400:
            entry = {
                "ts": _time.time(),
                "level": "WARN" if response.status_code >= 400 else "INFO",
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": duration_ms,
                "ip": request.client.host if request.client else "unknown",
                "user_agent": request.headers.get("user-agent", "")[:80],
                "request_id": request_id,
            }
            # Sprint 16.1 P1-4: print → logger
            if response.status_code >= 500:
                _access_logger.error("http_request", extra=entry)
            elif response.status_code >= 400:
                _access_logger.warning("http_request", extra=entry)
            else:
                _access_logger.info("http_request", extra=entry)

        # Sprint 5.2: 5xx → пишем в audit log (через отдельную сессию)
        if response.status_code >= 500:
            try:
                from app.db.session import SessionLocal
                from app.admin import service as audit_service
                from app.users.models import User

                # Пытаемся определить user из токена (best-effort)
                user_id = None
                auth = request.headers.get("authorization", "")
                if auth.startswith("Bearer "):
                    try:
                        from app.auth.security import decode_token
                        claim = decode_token(auth[7:])
                        user_id = int(claim.get("sub", 0))
                    except Exception:
                        pass

                s = SessionLocal()
                try:
                    user = None
                    if user_id:
                        user = s.get(User, user_id)
                    audit_service.record(
                        s,
                        user=user,
                        action="error.5xx",
                        entity="http_request",
                        details={
                            "method": request.method,
                            "path": request.url.path,
                            "status": response.status_code,
                            "request_id": request_id,
                        },
                    )
                finally:
                    s.close()

                # Sprint 16.0 P0-4: enqueue 5xx в Redis для alert worker.
                # Не отправляем sync httpx.post() в middleware — это блокирует
                # event loop. Вместо этого worker (app/bot/alert_worker.py)
                # читает из `ai:alerts` и шлёт в Telegram с dedupe.
                try:
                    import json as _json_alert
                    _redis_alert = _get_redis()
                    if _redis_alert is not None:
                        await _redis_alert.rpush(
                            "ai:alerts",
                            _json_alert.dumps({
                                "kind": "http_5xx",
                                "status": response.status_code,
                                "method": request.method,
                                "path": request.url.path,
                                "request_id": request_id,
                                "ts": _time.time(),
                            }),
                        )
                except Exception as alert_err:
                    import logging
                    logging.getLogger(__name__).warning(
                        "Failed to enqueue 5xx alert: %s", alert_err,
                    )

            except Exception as audit_err:
                # Sprint 16.0: логируем раньше, чем pass
                # Не даём observability сломать основной запрос,
                # но фиксируем факт сбоя (иначе audit gap незаметен).
                import logging
                logging.getLogger(__name__).error(
                    "Audit log failed: %s (request_id=%s, status=%s, path=%s)",
                    audit_err, request_id, response.status_code, request.url.path,
                    exc_info=True,
                )

        response.headers["x-request-id"] = request_id
        return response

    @app.middleware("http")
    async def request_context(request, call_next):
        """Сохраняет текущий Request в contextvar для audit log."""
        from app.admin.context import set_current_request, reset_current_request

        token = set_current_request(request)
        try:
            return await call_next(request)
        finally:
            reset_current_request(token)

    # Sprint 5.1 — Prometheus metrics middleware
    from app.observability import metrics_middleware

    @app.middleware("http")
    async def _prom_metrics_middleware(request, call_next):
        return await metrics_middleware(request, call_next)

    @app.get("/metrics", tags=["meta"], summary="Prometheus metrics")
    def prometheus_metrics(request: Request) -> Response:
        """Sprint 5.1 — метрики для Prometheus scraping.

        Sprint 16.1 P1-6: ограничены IP-адресами. /metrics содержит
        internal info (endpoint names, request cardinality) — не для
        публичного доступа. Разрешены:
        - 127.0.0.1 (localhost)
        - 172.19.0.5 (Prometheus container в deploy_external network)
        - 192.168.0.0/16 (LAN Prometheus scraper)
        """
        client_ip = request.client.host if request.client else ""
        # Если IP в белом списке — пропускаем.
        # Sprint 16.1 P1-6: testclient host тоже разрешён (pytest).
        allowed = (
            client_ip == "127.0.0.1"
            or client_ip == "172.19.0.5"
            or client_ip.startswith("192.168.")
            or client_ip.startswith("172.19.")
            or client_ip == "testclient"  # FastAPI TestClient в pytest
        )
        if not allowed:
            from fastapi.exceptions import HTTPException
            raise HTTPException(status_code=403, detail="Metrics access denied")
        from app.observability import metrics_endpoint

        return metrics_endpoint()

    @app.get("/", tags=["meta"], summary="Корневая заглушка")
    def root() -> dict[str, str]:
        return {
            "service": settings.app_name,
            "docs": "/docs",
            "health": "/health",
            "ready": "/ready",
        }

    # Роутеры предметной области
    from app.auth.router import router as auth_router
    from app.auth.oauth import router as oauth_router
    from app.voice.router import router as voice_router
    from app.rag_router import router as rag_router
    from app.v2 import router as v2_router  # Sprint 10.3 — /api/v2 каркас
    from app.v2.exercises import router as v2_exercises_router  # Pilot Core P1.2.3
    from app.auth.router import student_router as student_profile_router
    from app.subjects.router import router as subjects_router
    from app.subjects.router import topics_router
    from app.ai.router import router as ai_router
    from app.sessions.router import router as sessions_router  # Sprint 34
    from app.cgm.router import router as cgm_router  # Sprint 40: Nightscout proxy
    from app.progress.router import router as progress_router
    from app.diagnostics.router import router as diagnostic_router
    from app.parents.router import router as parents_router
    from app.parents.router import student_router as link_parent_router
    from app.materials.router import router as materials_router
    from app.admin.router import router as admin_router
    from app.admin.realtime import router as admin_realtime_router  # Sprint 9.3 — WS для админа
    from app.teacher.router import router as teacher_router
    from app.student.router import router as student_materials_router
    from app.student import models as _stu_models  # noqa: F401  (Alembic autogen + TopicDraft)
    from app.notifications.router import router as notifications_router
    from app.ai.websocket import router as ws_router
    from app.ai.websocket_more import router as ws_more_router

    app.include_router(auth_router)
    app.include_router(student_profile_router)
    app.include_router(subjects_router)
    app.include_router(topics_router)
    app.include_router(ai_router)
    app.include_router(sessions_router)  # Sprint 34
    app.include_router(cgm_router)  # Sprint 40
    app.include_router(progress_router)
    app.include_router(diagnostic_router)
    app.include_router(parents_router)
    app.include_router(link_parent_router)
    app.include_router(materials_router)
    app.include_router(admin_router)
    app.include_router(admin_realtime_router)
    app.include_router(teacher_router)
    app.include_router(student_materials_router)
    app.include_router(notifications_router)
    app.include_router(ws_router)
    app.include_router(ws_more_router)
    app.include_router(oauth_router)
    app.include_router(voice_router)
    app.include_router(rag_router)
    app.include_router(v2_router)
    app.include_router(v2_exercises_router)

    return app


app = create_app()


# Глобальный (в рамках процесса) rate-limit log. В production с несколькими
# воркерами uvicorn переключаем на Redis (REDIS_URL в env).
_ai_call_log: dict[int, list[float]] = {}
_login_attempts_log: dict[str, list[float]] = {}  # ip -> timestamps
_register_attempts_log: dict[str, list[float]] = {}  # ip -> timestamps (Sprint 4.1)


def _client_ip(request, trusted_proxies: list[str]) -> str:
    """Sprint 4.3: безопасное определение IP клиента.

    Доверяем X-Forwarded-For только если immediate peer в trusted_proxies.
    Иначе возвращаем request.client.host (нельзя подменить через XFF).
    """
    peer = request.client.host if request.client else "unknown"
    # Проверяем, что peer — доверенный прокси
    if trusted_proxies and _ip_in_cidrs(peer, trusted_proxies):
        xff = request.headers.get("x-forwarded-for")
        if xff:
            # Берём самый левый (первый IP в цепочке)
            return xff.split(",")[0].strip()
    return peer


def _ip_in_cidrs(ip: str, cidrs: list[str]) -> bool:
    """Проверяет, что IP входит в любой из CIDR-списков."""
    import ipaddress
    import socket

    try:
        # Если hostname — резолвим
        try:
            addr = ipaddress.ip_address(ip)
        except ValueError:
            addr = ipaddress.ip_address(socket.gethostbyname(ip))
        for cidr in cidrs:
            try:
                if addr in ipaddress.ip_network(cidr, strict=False):
                    return True
            except ValueError:
                continue
    except Exception:
        pass
    return False

# Заполняется в create_app() — нужно для /health (uptime)
_app_start_time: float = 0.0
_app_started_iso: str = ""

# Инициализируем сразу при импорте модуля, чтобы значения были доступны
# даже если create_app() не вызывалась (например, в TestClient).
import time as _init_time
from datetime import datetime as _init_dt, timezone as _init_tz
_app_start_time = _init_time.time()
_app_started_iso = _init_dt.now(_init_tz.utc).isoformat()
_ws_concurrent_log: dict[int, list[float]] = {}  # uid -> ws handshake times
_redis_client = None  # инициализируется при первом использовании


def _get_redis():
    """Ленивая инициализация Redis-клиента. Возвращает None если REDIS_URL не задан или недоступен."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    redis_url = os.environ.get("REDIS_URL", "").strip()
    if not redis_url:
        return None
    try:
        import redis.asyncio as aioredis

        _redis_client = aioredis.from_url(redis_url, decode_responses=True)
        return _redis_client
    except Exception:
        return None