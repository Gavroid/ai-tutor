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

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from app.auth.security import ACCESS_COOKIE
from app.common.deps import require_admin

from app.ai.budget import get_usage
from app.observability import metrics_payload
from app.users.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["admin-realtime"])


def _safe_int(v: object, default: int = 0) -> int:
    try:
        return int(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _iter_prometheus_samples(text: str):
    from prometheus_client.parser import text_string_to_metric_families

    for family in text_string_to_metric_families(text):
        for sample in family.samples:
            # sample = (name, labels, value, timestamp, exemplar, native_histogram)
            name = sample.name
            labels = dict(sample.labels or {})
            try:
                value = float(sample.value)
            except (TypeError, ValueError):
                continue
            yield name, labels, value


def parse_prometheus_snapshot(text: str) -> dict[str, object]:
    """Parse aggregated Prometheus text into the compact admin realtime payload."""
    ai_modes: dict[str, dict[str, int]] = {}
    ai_tokens: dict[str, int] = {}
    http_total: dict[str, int] = {"2xx": 0, "4xx": 0, "5xx": 0}
    http_breakdown: list[dict[str, object]] = []

    for name, labels, value in _iter_prometheus_samples(text):
        if name == "ai_requests_total":
            mode = labels.get("mode", "unknown")
            status = labels.get("status", "unknown")
            ai_modes.setdefault(mode, {"ok": 0, "error": 0})
            ai_modes[mode][status] = _safe_int(value)
        elif name == "ai_tokens_total":
            role = labels.get("role", "unknown")
            ai_tokens[role] = _safe_int(value)
        elif name == "http_requests_total":
            status = labels.get("status", "0")
            path = labels.get("path", "unknown")
            item = classify_http_status_sample(path, status, value)
            http_total[str(item["bucket"])] += _safe_int(item["count"])
            if item["bucket"] in ("4xx", "5xx") and item["count"]:
                http_breakdown.append(item)

    http_breakdown.sort(key=lambda item: (str(item["kind"]), str(item["status"]), str(item["path"])))
    return {
        "ai_modes": ai_modes,
        "ai_tokens": ai_tokens,
        "http_total": http_total,
        "http_breakdown": http_breakdown,
    }


def classify_http_status_sample(path: str, status: str, value: object) -> dict[str, object]:
    """Classify Prometheus HTTP counter samples for admin-facing monitoring.

    Expected 4xx are useful context but should not look like product blockers.
    Actionable values are candidates for alerts or manual investigation.
    """
    code = _safe_int(status)
    count = _safe_int(value)
    bucket = "5xx" if 500 <= code < 600 else "4xx" if 400 <= code < 500 else "2xx"
    kind = "ok"
    reason = "success"
    if bucket == "5xx":
        kind = "actionable"
        reason = "server_error"
    elif bucket == "4xx":
        expected = {
            ("/api/v1/student/topics/{topic_id}/draft", "404"): "missing_topic_draft",
            ("/api/v1/admin/realtime/snapshot", "401"): "unauthenticated_snapshot_probe",
        }
        reason = expected.get((path, status), "unexpected_4xx")
        kind = "expected" if reason != "unexpected_4xx" else "actionable"
    return {"path": path, "status": status, "count": count, "bucket": bucket, "kind": kind, "reason": reason}


def _metrics_snapshot() -> dict:
    """Снимок агрегированных метрик для админ-панели."""
    try:
        parsed = parse_prometheus_snapshot(metrics_payload().decode("utf-8", errors="replace"))
    except Exception as e:
        logger.debug("prometheus payload parse failed: %s", e)
        parsed = {
            "ai_modes": {},
            "ai_tokens": {},
            "http_total": {"2xx": 0, "4xx": 0, "5xx": 0},
            "http_breakdown": [],
        }

    sys = _system_health()
    return {
        "ts": datetime.now(timezone.utc).isoformat(),
        **parsed,
        "system": sys,
    }


def _system_health() -> dict:
    """Проверяет здоровье Docker-сервисов + память/CPU."""
    result = {"db": "unknown", "redis": "unknown", "backend": "unknown", "mem_used_pct": None, "mem_used_mb": None, "mem_limit_mb": None}
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
        current_path = "/sys/fs/cgroup/memory.current"
        max_path = "/sys/fs/cgroup/memory.max"
        with open(current_path) as f:
            used_bytes = _safe_int(f.read().strip())
        result["mem_used_mb"] = round(used_bytes / 1024 / 1024, 1)
        try:
            with open(max_path) as f:
                raw_limit = f.read().strip()
            if raw_limit and raw_limit != "max":
                limit_bytes = _safe_int(raw_limit)
                if limit_bytes > 0:
                    result["mem_limit_mb"] = round(limit_bytes / 1024 / 1024, 1)
                    result["mem_used_pct"] = round(used_bytes / limit_bytes * 100, 1)
        except Exception:
            pass
    except Exception:
        logger.debug("cgroup memory read failed", exc_info=True)
    return result


@router.get("/realtime/snapshot")
def admin_realtime_snapshot(current: User = Depends(require_admin())) -> dict:
    """Cookie-authenticated one-shot realtime snapshot for the admin UI.

    The WebSocket route remains for legacy callers, but production nginx does not
    reliably pass WS upgrade for /api/v1/admin/ws. HTTP polling is enough for the
    MVP admin panel and uses the same cookie auth path as the rest of the app.
    """
    snap = _metrics_snapshot()
    snap["admin_id"] = current.id
    return snap


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
async def admin_ws(ws: WebSocket, token: str | None = Query(None)) -> None:
    """WS endpoint для real-time метрик (admin only).

    Supports legacy JWT query tokens and the current cookie-based auth flow.
    The frontend's deprecated getToken() returns the sentinel "cookie"; in that
    case we read the httpOnly access cookie from the WebSocket handshake.
    """
    try:
        from app.auth.security import decode_token

        raw_token = token if token and token != "cookie" else ws.cookies.get(ACCESS_COOKIE)
        if not raw_token:
            await ws.close(code=1008, reason="missing token")
            return
        payload = decode_token(raw_token)
        if not payload or payload.get("type") != "access":
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
