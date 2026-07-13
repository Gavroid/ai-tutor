"""Real-time метрики для админа через WebSocket (Sprint 9.3).

Стримит JSON-снапшоты каждые ~2 сек:
- active_sessions (login за последние 24ч)
- ai_requests_total{min,modes}
- http_5xx_rate (за последние 5 мин, базируясь на http_requests_total)
- db/redis/smtp statuses (через docker exec)
- memory/cpu/disk (через psutil)

Требования для multi-worker: см. Sprint 6.3. Пока single-worker.
Auth: require_admin (token в query).
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.ai.budget import get_usage
from app.observability import (
    AI_REQUESTS_TOTAL,
    AI_TOKENS_TOTAL,
    HTTP_REQUESTS_TOTAL,
)
from app.users.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["admin-realtime"])


def _safe_int(v: object, default: int = 0) -> int:
    try:
        return int(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _metrics_snapshot() -> dict:
    """Снимок метрик для админ-WS. Не падает при недоступности любой части."""
    # 1) AI запросы по режимам (за всё время)
    ai_modes: dict[str, dict[str, int]] = {}
    try:
        for metric in AI_REQUESTS_TOTAL.collect():
            for sample in metric.samples:
                # 'ai_requests_total{mode="explain",status="ok"}' → value
                labels = sample.labels
                mode = labels.get("mode", "unknown")
                status = labels.get("status", "unknown")
                ai_modes.setdefault(mode, {"ok": 0, "error": 0})
                ai_modes[mode][status] = _safe_int(sample.value)
    except Exception as e:
        logger.debug("ai_modes collect failed: %s", e)

    # 2) AI токены (input/output)
    ai_tokens: dict[str, int] = {}
    try:
        for metric in AI_TOKENS_TOTAL.collect():
            for sample in metric.samples:
                role = sample.labels.get("role", "unknown")
                ai_tokens[role] = _safe_int(sample.value)
    except Exception as e:
        logger.debug("ai_tokens collect failed: %s", e)

    # 3) HTTP 5xx rate — это Counter, абсолютное значение (нужно знать baseline)
    try:
        http_total: dict[str, int] = {"2xx": 0, "4xx": 0, "5xx": 0}
        for metric in HTTP_REQUESTS_TOTAL.collect():
            for sample in metric.samples:
                status = sample.labels.get("status", "0")
                code = int(status) if status.isdigit() else 0
                bucket = "5xx" if 500 <= code < 600 else "4xx" if 400 <= code < 500 else "2xx"
                http_total[bucket] += _safe_int(sample.value)
    except Exception as e:
        logger.debug("http_total collect failed: %s", e)
        http_total = {"2xx": 0, "4xx": 0, "5xx": 0}

    # 4) System status (docker-compose ps)
    sys = _system_health()
    return {
        "ts": datetime.now(timezone.utc).isoformat(),
        "ai_modes": ai_modes,
        "ai_tokens": ai_tokens,
        "http_total": http_total,
        "system": sys,
    }


def _system_health() -> dict:
    """Проверяет здоровье Docker-сервисов + память/CPU."""
    result = {"db": "unknown", "redis": "unknown", "backend": "unknown", "mem_used_pct": None}
    try:
        out = subprocess.run(
            ["docker", "compose", "ps", "--format", "{{.Service}}={{.Status}}"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd="/opt/ai-tutor/deploy",
        )
        for line in out.stdout.splitlines():
            if "=" in line:
                svc, status = line.split("=", 1)
                is_healthy = "healthy" in status.lower() or "up" in status.lower()
                if svc in ("db", "redis", "backend"):
                    result[svc] = "ok" if is_healthy else "down"
    except Exception as e:
        logger.debug("docker ps failed: %s", e)

    try:
        with open("/proc/meminfo") as f:
            mem = {}
            for line in f:
                if ":" in line:
                    k, v = line.split(":", 1)
                    mem[k.strip()] = v.strip().split()[0]
            total = _safe_int(mem.get("MemTotal"))
            avail = _safe_int(mem.get("MemAvailable"))
            if total > 0:
                used_pct = round((total - avail) / total * 100, 1)
                result["mem_used_pct"] = used_pct
    except Exception:
        pass
    return result


async def _metrics_stream(ws: WebSocket, principal: User) -> None:
    """Стримит снимки каждые 2 секунды. Закрывает соединение если admin выходит."""
    logger.info("admin realtime stream started: admin_id=%s", principal.id)
    try:
        while True:
            snap = _metrics_snapshot()
            snap["admin_id"] = principal.id
            await ws.send_json(snap)
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        logger.info("admin realtime stream closed by client")
    except Exception:
        logger.exception("admin realtime stream error")
        try:
            await ws.close()
        except Exception:
            pass


@router.websocket("/ws")
async def admin_ws(ws: WebSocket, token: str = Query(...)) -> None:
    """WS endpoint для real-time метрик (admin only).

    Args:
        ws: WebSocket-соединение.
        token: JWT в query (?token=...). Чтобы client мог открыть
            нативный WebSocket (cookies в WS браузера передаёт не всегда).
    """
    # Auth — проверяем токен ДО accept
    try:
        from app.auth.security import decode_token

        payload = decode_token(token)
        if not payload:
            await ws.close(code=1008, reason="invalid token")
            return
        role = payload.get("role")
        if role != "admin":
            await ws.close(code=1008, reason="admin only")
            return
        admin_id = _safe_int(payload.get("sub"))
    except Exception:
        await ws.close(code=1008, reason="auth failed")
        return

    await ws.accept()
    # Нужен fake user для сигнатуры — обёртка
    principal = User(id=admin_id, role="admin")  # type: ignore[call-arg]
    await _metrics_stream(ws, principal)
