"""WebSocket-роутер для стриминга ответов AI в реальном времени.

Поток: токены приходят по одному через WebSocket (text-сообщения).
После завершения приходит финальное сообщение с метаданными (model, tokens).
"""
from __future__ import annotations

import asyncio
import json
import logging
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.ai.service import get_ai_service
from app.auth.security import decode_token
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)
# Sprint 83: WS keepalive + max lifetime.
# Защита от hung connections (WS может висеть вечно без ping/pong).
WS_MAX_LIFETIME_SECONDS = 3600  # 1 час max connection
WS_PING_INTERVAL_SECONDS = 30    # ping каждые 30 сек


router = APIRouter(tags=["websocket"])


@router.websocket("/ws/ai/chat")
async def ai_chat_stream(websocket: WebSocket):
    """Стриминг ответов AI по WebSocket.

    Протокол:
    - Клиент подключается с cookie `access_token` (httponly, set by /login, /refresh).
    - Sprint 66: query string ?token= больше НЕ поддерживается (security fix).
    - Клиент шлёт JSON: {"history": [...], "topic_id": 1}
    - Сервер стримит куски текста: {"type": "chunk", "content": "..."}
    - В конце: {"type": "done", "model": "MiniMax-M3"}
    - При ошибке: {"type": "error", "message": "..."}

    Sprint 16.0 P0-3 (security): JWT в query string попадает в nginx access
    logs, browser history, exception traces. Sprint 16.1 P1-2 мигрировал
    frontend на cookie-based auth, и Sprint 66 убирает query string
    fallback полностью — только cookie `access_token`.
    """
    # Sprint 66: только cookie auth (Sprint 16.1 P1-2 migration).
    # Query string fallback УБРАН (security: nginx access logs, browser history).
    token = websocket.cookies.get("access_token")
    if not token:
        await websocket.close(code=1008, reason="Missing token (cookie required)")
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

    # Sprint 16.1 P1-3 + Sprint 69: AI budget guard на WS уровне.
    # Без проверки user мог открыть WS и бомбить AI запросами напрямую.
    # Sprint 69: admin role bypasses budget (operational necessity).
    # Загружаем user из БД для role check.
    try:
        from app.db.session import SessionLocal
        from app.users import models as user_models
        from app.ai.budget import BudgetExceeded, check_and_increment

        with SessionLocal() as db_session:
            user = db_session.get(user_models.User, user_id)
            if user is None:
                await websocket.close(code=1008, reason="User not found")
                return
            if user.role != user_models.Role.ADMIN:
                check_and_increment(user_id)
    except BudgetExceeded as e:
        logger.warning("WS budget exceeded user_id=%s: %s/%s", user_id, e.used, e.limit)
        await websocket.close(code=1008, reason=f"AI budget exceeded: {e.limit_kind}")
        return

    await websocket.accept()

    # Sprint 83: keepalive + max lifetime.
    # Background task sends ping каждые 30 сек; основной loop работает с timeout.
    start_time = time.time()
    last_ping_time = start_time

    async def _send_pings():
        nonlocal last_ping_time
        while True:
            await asyncio.sleep(WS_PING_INTERVAL_SECONDS)
            elapsed = time.time() - start_time
            if elapsed > WS_MAX_LIFETIME_SECONDS:
                logger.info("WS max lifetime exceeded user_id=%s elapsed=%ss", user_id, int(elapsed))
                await websocket.close(code=1008, reason="Max lifetime exceeded")
                return
            try:
                await websocket.send_json({"type": "ping", "ts": int(time.time())})
                last_ping_time = time.time()
            except Exception:
                return

    ping_task = asyncio.create_task(_send_pings())

    try:
        while True:
            # Calculate remaining time
            elapsed = time.time() - start_time
            if elapsed > WS_MAX_LIFETIME_SECONDS:
                await websocket.close(code=1008, reason="Max lifetime exceeded")
                break

            try:
                # Receive with timeout (slightly larger than ping interval)
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=WS_PING_INTERVAL_SECONDS * 2,
                )
            except asyncio.TimeoutError:
                # No message received — that's OK, just continue
                continue
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
        # Sprint 84: cancel background ping task (memory leak fix).
        # ping_task создан в начале цикла, должен быть отменён при выходе.
        try:
            ping_task.cancel()
        except Exception:
            pass
        try:
            await websocket.close()
        except Exception:
            pass