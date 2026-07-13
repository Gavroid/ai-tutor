"""Speech-to-Text endpoint.

Поддерживает:
- OpenAI-compatible ASR endpoint (если настроен WHISPER_API_URL)
- Локальный Whisper (если есть в системе)
- Fallback: 503 если ничего не настроено

Sprint 7.2: rate-limit 20 запросов/мин на пользователя через in-memory dict.
В multi-worker среде можно расширить до Redis (Sprint 10 backlog).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
from collections import defaultdict, deque
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.auth.security import get_current_user
from app.users.models import User

router = APIRouter(prefix="/api/v1/voice", tags=["voice"])

ALLOWED_AUDIO_EXTS = {".wav", ".mp3", ".ogg", ".m4a", ".webm", ".flac"}
MAX_AUDIO_BYTES = 25 * 1024 * 1024  # 25 MB

# Sprint 7.2 — rate-limit: 20 calls/min per user (in-memory, single-worker).
VOICE_RATE_LIMIT_PER_MIN = 20
_voice_calls: dict[int, deque[float]] = defaultdict(deque)


def _check_voice_rate_limit(user_id: int) -> None:
    """Raise 429 если превышен лимит."""
    now = time.time()
    dq = _voice_calls[user_id]
    # Очищаем окно старше 60 сек
    while dq and (now - dq[0]) > 60.0:
        dq.popleft()
    if len(dq) >= VOICE_RATE_LIMIT_PER_MIN:
        raise HTTPException(
            429,
            f"Voice rate limit exceeded: max {VOICE_RATE_LIMIT_PER_MIN}/min",
        )
    dq.append(now)


@router.post("/transcribe")
async def transcribe(
    file: UploadFile = File(...),
    language: str = "ru",
    current: User = Depends(get_current_user),
):
    """Transcribe audio → text.

    Args:
        file: аудио файл (wav/mp3/ogg/m4a/webm/flac)
        language: ISO код языка (ru, en, ...)

    Returns:
        {"text": "...", "language": "ru", "duration_seconds": N}
    """
    # Sprint 7.2: rate-limit (защита от абьюза Whisper API и загруза сервера).
    _check_voice_rate_limit(current.id)

    # Validate extension
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_AUDIO_EXTS:
        raise HTTPException(
            400,
            f"Unsupported audio format: {ext}. Allowed: {ALLOWED_AUDIO_EXTS}",
        )

    # Save to temp file
    contents = await file.read()
    if len(contents) > MAX_AUDIO_BYTES:
        raise HTTPException(413, f"Audio too large ({len(contents)} bytes, max {MAX_AUDIO_BYTES})")

    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        # Try OpenAI-compatible Whisper API
        whisper_url = os.environ.get("WHISPER_API_URL", "").strip()
        whisper_key = os.environ.get("WHISPER_API_KEY", "").strip()
        whisper_model = os.environ.get("WHISPER_MODEL", "whisper-1")

        if whisper_url:
            return await _transcribe_via_api(
                tmp_path, whisper_url, whisper_key, whisper_model, language
            )

        # Try local whisper
        if shutil.which("whisper"):
            return _transcribe_local_whisper(tmp_path, language)

        # Try ffmpeg + speech recognition fallback
        return _transcribe_ffmpeg_stub(tmp_path, language)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


async def _transcribe_via_api(
    tmp_path: str,
    url: str,
    key: str,
    model: str,
    language: str,
) -> dict:
    """OpenAI-compatible Whisper API."""
    headers = {}
    if key:
        headers["Authorization"] = f"Bearer {key}"

    async with httpx.AsyncClient(timeout=60) as client:
        with open(tmp_path, "rb") as f:
            files = {"file": (Path(tmp_path).name, f, "audio/wav")}
            data = {"model": model, "language": language}
            r = await client.post(f"{url.rstrip('/')}/v1/audio/transcriptions", headers=headers, files=files, data=data)

        if r.status_code != 200:
            raise HTTPException(502, f"Whisper API error {r.status_code}: {r.text[:200]}")

        body = r.json()
        return {
            "text": body.get("text", ""),
            "language": language,
            "engine": "openai-api",
        }


def _transcribe_local_whisper(tmp_path: str, language: str) -> dict:
    """Local Whisper через CLI."""
    with tempfile.TemporaryDirectory() as outdir:
        cmd = [
            "whisper",
            tmp_path,
            "--language", language,
            "--output_format", "json",
            "--output_dir", outdir,
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=120)
        if result.returncode != 0:
            raise HTTPException(500, f"whisper failed: {result.stderr.decode()[:200]}")
        # Читаем JSON output
        json_files = list(Path(outdir).glob("*.json"))
        if not json_files:
            raise HTTPException(500, "whisper produced no output")
        import json as _json

        with open(json_files[0]) as f:
            data = _json.load(f)
        return {
            "text": data.get("text", ""),
            "language": data.get("language", language),
            "engine": "local-whisper",
            "duration_seconds": data.get("duration", 0),
        }


def _transcribe_ffmpeg_stub(tmp_path: str, language: str) -> dict:
    """Stub: проверяем что ffmpeg есть и говорим что ASR не настроен."""
    if not shutil.which("ffmpeg"):
        raise HTTPException(
            503,
            "Speech-to-text не настроен. Установите WHISPER_API_URL или whisper CLI.",
        )
    # Если только ffmpeg — не хватает ASR движка
    raise HTTPException(
        503,
        "ASR движок не найден. Установите whisper (pip install openai-whisper) или "
        "задайте WHISPER_API_URL для OpenAI-compatible ASR.",
    )
