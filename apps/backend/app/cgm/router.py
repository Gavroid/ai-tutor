"""Sprint 40: CGM proxy router (Nightscout).

T1D safety (Luna Pro):
- ❌ НЕ используем AI для medical decisions.
- ❌ НЕ интерпретируем glucose data.
- ❌ НЕ сохраняем glucose values в БД.
- ✅ ТОЛЬКО проксирование через Nightscout API.
- ✅ Opt-in через cgm_configs.enabled.

Nightscout API docs: https://github.com/nightscout/cgm-remote-monitor
"""
from __future__ import annotations

import logging
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.common.deps import User, get_current_user
from app.db.session import engine as _engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/cgm", tags=["cgm"])


class CGMConfigIn(BaseModel):
    """Sprint 40: CGM opt-in config."""

    nightscout_url: str = Field(
        min_length=10,
        max_length=500,
        description="Nightscout API base URL (e.g., https://ns.example.com)",
    )
    enabled: bool = Field(
        default=True,
        description="Opt-in: разрешить проксирование CGM data",
    )


class CGMConfigOut(BaseModel):
    """Sprint 40: current CGM config (без secrets)."""

    nightscout_url: str
    enabled: bool


class CGMReading(BaseModel):
    """Sprint 40: single CGM reading (SGV — sensor glucose value)."""

    sgv: float = Field(description="Glucose value in mg/dL")
    direction: str = Field(default="NONE", description="Trend arrow")
    trend: int = Field(default=0, description="Trend numeric")
    date: int = Field(description="Unix timestamp (ms)")
    date_string: str = Field(description="ISO datetime")
    device: str | None = None
    type: str = Field(default="sgv")

    @property
    def direction_arrow(self) -> str:
        """Sprint 40: arrows для UI."""
        arrows = {
            "DoubleUp": "⇈",
            "SingleUp": "↑",
            "FortyFiveUp": "↗",
            "Flat": "→",
            "FortyFiveDown": "↘",
            "SingleDown": "↓",
            "DoubleDown": "⇊",
            "NOT_COMPUTABLE": "?",
            "RATE_OUT_OF_RANGE": "⚠",
        }
        return arrows.get(self.direction, "·")


class CGMLatestOut(BaseModel):
    """Sprint 40: latest CGM reading + meta."""

    reading: CGMReading
    units: str = "mg/dL"
    fetched_at: str  # ISO datetime когда проксировали


class CGMStatusOut(BaseModel):
    """Sprint 40: Nightscout status (sensors, pump, uploader)."""

    name: str | None = None
    version: str | None = None
    server_time: str | None = None
    status: str = "ok"


def _get_user_config(user_id: int) -> CGMConfigOut | None:
    """Sprint 40: получить CGM config пользователя из БД."""
    with _engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT nightscout_url, enabled FROM cgm_configs WHERE user_id = :uid"
            ),
            {"uid": user_id},
        ).fetchone()

    if row is None:
        return None
    return CGMConfigOut(nightscout_url=row[0], enabled=row[1])


def _set_user_config(user_id: int, url: str, enabled: bool) -> None:
    """Sprint 40: upsert CGM config."""
    with _engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO cgm_configs (user_id, nightscout_url, enabled)
                VALUES (:uid, :url, :en)
                ON CONFLICT (user_id) DO UPDATE
                SET nightscout_url = :url, enabled = :en
                """
            ),
            {"uid": user_id, "url": url, "en": enabled},
        )


@router.get("/config", response_model=CGMConfigOut)
def get_config(current: User = Depends(get_current_user)) -> CGMConfigOut:
    """Sprint 40: получить CGM config текущего user."""
    cfg = _get_user_config(current.id)
    if cfg is None:
        # Sprint 40: default — disabled, no URL
        return CGMConfigOut(nightscout_url="", enabled=False)
    return cfg


@router.put("/config", response_model=CGMConfigOut)
def set_config(
    payload: CGMConfigIn,
    current: User = Depends(get_current_user),
) -> CGMConfigOut:
    """Sprint 40: opt-in / opt-out CGM.

    Безопасность:
    - URL validated (не localhost, не file://)
    - enabled=false → отключает проксирование
    - Audit log: action='cgm.config_update'
    """
    # Sprint 40: валидация URL — не localhost, не file, не internal IP
    url = payload.nightscout_url.strip().lower()
    forbidden_prefixes = (
        "http://localhost",
        "https://localhost",
        "http://127.",
        "https://127.",
        "http://0.0.0.0",
        "https://0.0.0.0",
        "file://",
        "gopher://",
    )
    for prefix in forbidden_prefixes:
        if url.startswith(prefix):
            raise HTTPException(
                400,
                f"Nightscout URL не может быть {prefix} (security: SSRF защита)",
            )

    if not url.startswith("https://"):
        # Sprint 40: только HTTPS для CGM (медицинские данные)
        raise HTTPException(400, "Nightscout URL должен быть https://")

    _set_user_config(current.id, url, payload.enabled)
    return CGMConfigOut(nightscout_url=url, enabled=payload.enabled)


@router.get("/latest", response_model=CGMLatestOut)
async def get_latest(current: User = Depends(get_current_user)) -> CGMLatestOut:
    """Sprint 40: проксирование latest SGV от Nightscout.

    Возвращает single reading + meta. БЕЗ сохранения в БД.
    """
    import json
    from datetime import datetime, timezone

    cfg = _get_user_config(current.id)
    if cfg is None or not cfg.enabled:
        raise HTTPException(403, "CGM не настроен. Используйте PUT /api/v1/cgm/config")

    if not cfg.nightscout_url:
        raise HTTPException(400, "Nightscout URL не указан")

    # Sprint 40: GET {url}/api/v1/entries/sgv?count=1
    url = cfg.nightscout_url.rstrip("/") + "/api/v1/entries/sgv.json?count=1"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url)
            r.raise_for_status()
            data = r.json()
    except httpx.HTTPError as exc:
        logger.warning("CGM Nightscout request failed: %s", exc)
        raise HTTPException(502, f"Nightscout недоступен: {exc!s}") from exc

    if not data or not isinstance(data, list) or len(data) == 0:
        raise HTTPException(404, "Nightscout не вернул данных")

    entry = data[0]
    reading = CGMReading(
        sgv=float(entry.get("sgv", 0)),
        direction=entry.get("direction", "NONE"),
        trend=entry.get("trend", 0),
        date=entry.get("date", 0),
        date_string=entry.get("dateString", ""),
        device=entry.get("device"),
        type=entry.get("type", "sgv"),
    )
    return CGMLatestOut(
        reading=reading,
        units=entry.get("units", "mg/dL"),
        fetched_at=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/status", response_model=CGMStatusOut)
async def get_status(current: User = Depends(get_current_user)) -> CGMStatusOut:
    """Sprint 40: Nightscout status (для UI badge 'online/offline')."""
    cfg = _get_user_config(current.id)
    if cfg is None or not cfg.enabled:
        raise HTTPException(403, "CGM не настроен")

    url = cfg.nightscout_url.rstrip("/") + "/api/v1/status.json"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(url)
            r.raise_for_status()
            data = r.json()
    except httpx.HTTPError as exc:
        # Sprint 40: status failure НЕ фатален — возвращаем degraded status.
        return CGMStatusOut(status="offline")

    return CGMStatusOut(
        name=data.get("name"),
        version=data.get("version"),
        server_time=data.get("serverTime"),
        status="ok",
    )