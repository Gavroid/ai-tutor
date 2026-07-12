"""WebSocket-роутер для стриминга ответов AI в реальном времени.

Поток: токены приходят по одному через WebSocket (text-сообщения).
После завершения приходит финальное сообщение с метаданными (model, tokens).
"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.ai.service import get_ai_service
from app.auth.security import decode_token
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/ai/chat")
async def ai_chat_stream(websocket: WebSocket):
    """Стриминг ответов AI по WebSocket.

    Протокол:
    - Клиент подключается с токеном: `ws://host/ws/ai/chat?token=<jwt>`
    - Клиент шлёт JSON: {"history": [...], "topic_id": 1}
    - Сервер стримит куски текста: {"type": "chunk", "content": "..."}
    - В конце: {"type": "done", "model": "MiniMax-M3"}
    - При ошибке: {"type": "error", "message": "..."}
    """
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008, reason="Missing token")
        return

    try:
        payload = decode_token(token)
    except Exception:
        await websocket.close(code=1008, reason="Invalid token")
        return

    user_id = int(payload.get("sub", 0))
    if not user_id:
        await websocket.close(code=1008, reason="Invalid token payload")
        return

    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON"})
                continue

            history = msg.get("history", [])
            topic_id = msg.get("topic_id")

            # Получаем тему если есть
            subject_name = topic_name = None
            if topic_id:
                with SessionLocal() as db:
                    from app.subjects import models as subj_models

                    t = db.get(subj_models.Topic, topic_id)
                    if t:
                        subject_name = t.section.subject.name
                        topic_name = t.name

            svc = get_ai_service()

            # Полный ответ (без стриминга на уровне провайдера пока)
            # Для MVP стримим посимвольно для UX
            resp = await svc.chat(history, subject_name, topic_name)

            # Имитация стриминга — посимвольная отправка
            content = resp.content
            chunk_size = max(1, len(content) // 30)  # ~30 чанков
            for i in range(0, len(content), chunk_size):
                chunk = content[i : i + chunk_size]
                await websocket.send_json({"type": "chunk", "content": chunk})

            await websocket.send_json(
                {
                    "type": "done",
                    "model": resp.model,
                    "input_tokens": resp.input_tokens,
                    "output_tokens": resp.output_tokens,
                }
            )
    except WebSocketDisconnect:
        logger.info("WS client disconnected (user_id=%s)", user_id)
    except Exception as exc:
        logger.exception("WS error")
        try:
            await websocket.send_json({"type": "error", "message": repr(exc)})
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass