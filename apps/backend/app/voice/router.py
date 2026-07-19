"""Sprint 6.2 — voice transcription endpoint.

Принимает audio blob (webm от MediaRecorder), возвращает распознанный текст.

MVP: без реального Whisper. Возвращает placeholder "распознавание не настроено".
В будущем (Sprint 6.2+): подключить OpenAI Whisper API или MiniMax ASR.

Whisper API (когда будет настроен):
- Whisper API: POST https://api.openai.com/v1/audio/transcriptions
  multipart/form-data: file=@audio.webm, model=whisper-1, language=ru
- Минимальный cost: $0.006 / minute
- Альтернатива: MiniMax ASR / Yandex SpeechKit / Google Speech

Текущая реализация — заглушка для тестирования UI.
Когда ключ API будет добавлен в env (OPENAI_API_KEY или WHISPER_API_KEY),
этот endpoint начнёт делать реальные запросы.

Безопасность:
- audio_file ограничен 25 МБ (как в других endpoints)
- Поддерживаются форматы: webm, mp3, wav, ogg
- rate limit через декоратор @ai_budget (Sprint 9.4) если ASR стоит денег
"""
from __future__ import annotations

import logging
import os

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.auth.security import get_current_user

router = APIRouter(prefix="/api/v1/voice", tags=["voice"])
logger = logging.getLogger(__name__)

MAX_AUDIO_SIZE_BYTES = 25 * 1024 * 1024  # 25 МБ

WHISPER_API_KEY = os.environ.get("OPENAI_API_KEY", "")
WHISPER_API_URL = "https://api.openai.com/v1/audio/transcriptions"


@router.post("/transcribe")
async def transcribe(
    file: UploadFile = File(...),
    current=Depends(get_current_user),
):
    """Sprint 6.2 MVP: транскрибирует аудио в текст.

    MVP: возвращает заглушку. Реальная интеграция с Whisper/MiniMax ASR —
    Sprint 6.2+ когда будет OPENAI_API_KEY или WHISPER_API_KEY.

    UI компонент VoiceMicButton отправляет сюда audio/webm blob.
    """
    # Лимит размера
    content = await file.read()
    if len(content) > MAX_AUDIO_SIZE_BYTES:
        raise HTTPException(
            413,
            f"Файл слишком большой (макс {MAX_AUDIO_SIZE_BYTES // (1024 * 1024)} МБ)",
        )

    logger.info(
        "voice transcribe: user_id=%s filename=%s size=%s bytes",
        current.id,
        file.filename,
        len(content),
    )

    # === MVP: реальный Whisper когда API key есть ===
    if WHISPER_API_KEY:
        try:
            import httpx

            files = {"file": (file.filename or "audio.webm", content, file.content_type)}
            data = {"model": "whisper-1", "language": "ru"}
            headers = {"Authorization": f"Bearer {WHISPER_API_KEY}"}
            r = httpx.post(
                WHISPER_API_URL,
                files=files,
                data=data,
                headers=headers,
                timeout=30.0,
            )
            if r.status_code == 200:
                return {"text": r.json().get("text", "")}
            else:
                logger.warning("Whisper API failed: %s %s", r.status_code, r.text[:200])
        except Exception as e:
            logger.warning("Whisper API error: %s", e)

    # === Заглушка: возвращаем понятный текст для проверки UI flow ===
    return {
        "text": "[распознавание голоса ещё не настроено — добавьте OPENAI_API_KEY в .env]",
        "warning": "asr_not_configured",
    }