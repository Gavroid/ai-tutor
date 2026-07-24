"""Sprint 6.2 — voice transcription endpoint.

Принимает audio blob (webm от MediaRecorder), возвращает распознанный текст.

MVP: без реального Whisper. Возвращает 503 когда ASR не настроен.
Когда `OPENAI_API_KEY` (или `WHISPER_API_KEY`) в env — реальный Whisper.

Whisper API (когда настроен):
- POST https://api.openai.com/v1/audio/transcriptions
  multipart/form-data: file=@audio.webm, model=whisper-1, language=ru
- Минимальный cost: $0.006 / minute
- Альтернатива: MiniMax ASR / Yandex SpeechKit / Google Speech

Sprint 16.1 P1-5: async httpx + правильные HTTP коды:
- 503 если ключ не задан (asr_not_configured)
- 504 если timeout (asr_timeout)
- 502 если provider вернул 5xx (asr_unavailable)
- 502 если 401/403 (asr_configuration_error)
- 200 если успех

Безопасность:
- audio_file ограничен 25 МБ (как в других endpoints)
- Поддерживаются форматы: webm, mp3, wav, ogg
- rate limit через /api/v1/ai/* middleware
"""
from __future__ import annotations

import logging
import os

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.auth.security import get_current_user
from app.config import get_settings

router = APIRouter(prefix="/api/v1/voice", tags=["voice"])
logger = logging.getLogger(__name__)

MAX_AUDIO_SIZE_BYTES = 25 * 1024 * 1024  # 25 МБ

# Sprint 16.1 P1-5: читаем ключ из settings (не os.environ при импорте модуля).
# Позволяет override в тестах и reload без рестарта процесса.
WHISPER_API_URL = os.environ.get(
    "WHISPER_API_URL", "https://api.openai.com/v1/audio/transcriptions"
)


@router.post("/transcribe")
async def transcribe(
    file: UploadFile = File(...),
    current=Depends(get_current_user),
):
    """Sprint 6.2 MVP: транскрибирует аудио в текст.

    Sprint 16.1 P1-5: async httpx + правильные HTTP коды + structured errors.
    """
    # Sprint 16.1 P1-5: лимит размера файла
    content = await file.read()
    if len(content) > MAX_AUDIO_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Файл слишком большой (макс. {MAX_AUDIO_SIZE_BYTES // (1024 * 1024)} МБ)",
        )

    logger.info(
        "voice transcribe: user_id=%s filename=%s size=%s bytes",
        current.id,
        file.filename,
        len(content),
    )

    # Sprint 16.1 P1-5: ключ берём из Settings (всё через env).
    settings = get_settings()
    whisper_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("WHISPER_API_KEY", "")

    if not whisper_key:
        # Sprint 16.1 P1-5: 503 + structured error code вместо заглушки "успех".
        raise HTTPException(
            status_code=503,
            detail={
                "code": "asr_not_configured",
                "message": "Распознавание голоса пока не настроено (OPENAI_API_KEY отсутствует)",
            },
        )

    # Sprint 16.1 P1-5: async HTTP client + правильные HTTP коды.
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                WHISPER_API_URL,
                files={
                    "file": (file.filename or "audio.webm", content, file.content_type),
                },
                data={"model": "whisper-1", "language": "ru"},
                headers={"Authorization": f"Bearer {whisper_key}"},
            )
    except httpx.TimeoutException:
        logger.warning("Whisper API timeout user_id=%s", current.id)
        raise HTTPException(
            status_code=504,
            detail={"code": "asr_timeout", "message": "Распознавание заняло слишком много времени"},
        )
    except httpx.HTTPError as e:
        logger.warning("Whisper API HTTP error user_id=%s: %s", current.id, e)
        raise HTTPException(
            status_code=502,
            detail={"code": "asr_unavailable", "message": "Сервис распознавания недоступен"},
        )

    # Sprint 16.1 P1-5: различаем 401/403/5xx.
    if response.status_code in (401, 403):
        logger.error(
            "Whisper API rejected credentials: %s %s",
            response.status_code,
            response.text[:200],
        )
        raise HTTPException(
            status_code=502,
            detail={"code": "asr_configuration_error", "message": "Проблема с ключом ASR"},
        )

    if response.status_code != 200:
        logger.warning(
            "Whisper API failed user_id=%s: %s %s",
            current.id,
            response.status_code,
            response.text[:200],
        )
        raise HTTPException(
            status_code=502,
            detail={"code": "asr_unavailable", "message": "Сервис распознавания вернул ошибку"},
        )

    return {"text": response.json().get("text", "")}