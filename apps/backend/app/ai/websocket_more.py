"""AI streaming endpoints (Этап UX — расширение).

Стримит chunks ответа AI через WebSocket. Аналог /ws/ai/chat,
но для explain/hint/generate (которые историю не используют).

Sprint 16.0 P0-3 (security): JWT в query string попадает в nginx access
logs, browser history, exception traces. Теперь принимаем и cookie
`access_token`, и query `?token=` (для обратной совместимости).
"""
from __future__ import annotations

import json
import logging

from app.ai.service import get_ai_service
from app.auth.security import ACCESS_COOKIE, decode_token
from app.db.session import SessionLocal
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/ai/explain")
async def ai_explain_stream(websocket: WebSocket):
    """Стриминг объяснения темы.

    Клиент: {"topic_id": 1}
    Сервер: {"type": "chunk", "content": "..."} → {"type": "done", "model": "..."}
    """
    # Sprint 66: только cookie auth (Sprint 16.1 P1-2 migration).
    # Query string fallback УБРАН (security: nginx access logs).
    token = websocket.cookies.get(ACCESS_COOKIE)
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

    # Sprint 69: AI budget guard на WS уровне (admin bypass).
    try:
        from app.ai.budget import BudgetExceeded, check_and_increment
        from app.db.session import SessionLocal
        from app.users import models as user_models

        with SessionLocal() as db_session:
            user = db_session.get(user_models.User, user_id)
            if user is None:
                await websocket.close(code=1008, reason="User not found")
                return
            if user.role != user_models.Role.ADMIN:
                check_and_increment(user_id)
    except BudgetExceeded as e:
        logger.warning(
            "WS budget exceeded user_id=%s: %s/%s", user_id, e.used, e.limit,
        )
        await websocket.close(code=1008, reason=f"AI budget exceeded: {e.limit_kind}")
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

            topic_id = msg.get("topic_id")
            if not topic_id:
                await websocket.send_json({"type": "error", "message": "topic_id required"})
                continue

            # Загружаем тему + пользователя
            with SessionLocal() as db:
                from app.subjects import models as subj_models
                from app.users import models as user_models

                topic = db.get(subj_models.Topic, topic_id)
                if topic is None:
                    await websocket.send_json({"type": "error", "message": "Topic not found"})
                    continue
                user = db.get(user_models.User, user_id)
                if user is None:
                    await websocket.send_json({"type": "error", "message": "User not found"})
                    continue

                svc = get_ai_service()
                resp = await svc.explain_topic(db, user, topic)

            # Стримим посимвольно (имитация стриминга для UX)
            content = resp.content
            chunk_size = max(1, len(content) // 30)
            for i in range(0, len(content), chunk_size):
                await websocket.send_json({"type": "chunk", "content": content[i : i + chunk_size]})

            await websocket.send_json(
                {
                    "type": "done",
                    "model": resp.model,
                    "input_tokens": resp.input_tokens,
                    "output_tokens": resp.output_tokens,
                }
            )
    except WebSocketDisconnect:
        logger.info("WS /ws/ai/explain disconnected (user_id=%s)", user_id)
    except Exception as exc:
        logger.exception("WS /ws/ai/explain error")
        try:
            await websocket.send_json({"type": "error", "message": repr(exc)})
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


@router.websocket("/ws/ai/generate")
async def ai_generate_stream(websocket: WebSocket):
    """Стриминг генерации задания.

    Клиент: {"topic_id": 1, "difficulty": 3}
    Сервер: {"type": "chunk", "content": "..."} → {"type": "done", "exercise": {...}}
    """
    # Sprint 66: только cookie auth (Sprint 16.1 P1-2 migration).
    # Query string fallback УБРАН (security: nginx access logs).
    token = websocket.cookies.get(ACCESS_COOKIE)
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

    # Sprint 69: AI budget guard на WS уровне (admin bypass).
    try:
        from app.ai.budget import BudgetExceeded, check_and_increment
        from app.db.session import SessionLocal
        from app.users import models as user_models

        with SessionLocal() as db_session:
            user = db_session.get(user_models.User, user_id)
            if user is None:
                await websocket.close(code=1008, reason="User not found")
                return
            if user.role != user_models.Role.ADMIN:
                check_and_increment(user_id)
    except BudgetExceeded as e:
        logger.warning(
            "WS budget exceeded user_id=%s: %s/%s", user_id, e.used, e.limit,
        )
        await websocket.close(code=1008, reason=f"AI budget exceeded: {e.limit_kind}")
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

            topic_id = msg.get("topic_id")
            difficulty = int(msg.get("difficulty", 2))
            if not topic_id:
                await websocket.send_json({"type": "error", "message": "topic_id required"})
                continue

            with SessionLocal() as db:
                from app.subjects import models as subj_models

                topic = db.get(subj_models.Topic, topic_id)
                if topic is None:
                    await websocket.send_json({"type": "error", "message": "Topic not found"})
                    continue

                svc = get_ai_service()
                gen = await svc.generate_exercise(
                    topic.section.subject.name, topic.name, difficulty
                )

            exercise = {
                "question_text": gen.question_text,
                "type": gen.type,
                "options": gen.options,
                "correct_answer": gen.correct_answer,
                "explanation": gen.explanation,
                "typical_mistakes": gen.typical_mistakes,
            }
            await websocket.send_json({"type": "done", "exercise": exercise, "model": "mock"})
    except WebSocketDisconnect:
        logger.info("WS /ws/ai/generate disconnected (user_id=%s)", user_id)
    except Exception as exc:
        logger.exception("WS /ws/ai/generate error")
        try:
            await websocket.send_json({"type": "error", "message": repr(exc)})
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
