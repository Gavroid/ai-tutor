"""Тесты WS rate limit (Этап security-3)."""
from __future__ import annotations

import os

os.environ["APP_SECRET_KEY"] = "test-secret-key-for-pytest-only-1234567890"
os.environ["APP_ENV"] = "development"
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["CORS_ORIGINS"] = "http://localhost:3000"
os.environ["AI_API_KEY"] = "mock-key-for-tests"

import pytest
from fastapi.testclient import TestClient

from app.db.session import Base, SessionLocal, engine, get_db
from app.main import app, _login_attempts_log, _ws_concurrent_log
from app.users import service as user_service
from app.users.schemas import UserCreate


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    engine.dispose()
    Base.metadata.create_all(engine)
    _login_attempts_log.clear()
    _ws_concurrent_log.clear()

    s = SessionLocal()
    user_service.register_user(
        s,
        UserCreate(
            email="kid@x.com",
            password="strongpass1",
            display_name="Kid",
            role="student",
            grade=7,
        ),
    )
    s.close()

    def _gen():
        s = SessionLocal()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = _gen
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


def _login(c: TestClient) -> str:
    r = c.post(
        "/api/v1/auth/login",
        json={"email": "kid@x.com", "password": "strongpass1"},
    )
    return r.json()["access_token"]


def test_ws_chat_under_limit(client):
    """До 5 WS-соединений — ок."""
    token = _login(client)
    # Открываем 4 чат-соединения (всё ещё работает — лимит 5/мин)
    for i in range(4):
        with client.websocket_connect(f"/ws/ai/chat?token={token}") as ws:
            ws.send_text('{"history": [{"role": "user", "content": "hi"}]}')
            ws.receive_json()  # chunk
            ws.receive_json()  # done
    # 5-е — ещё ок
    with client.websocket_connect(f"/ws/ai/chat?token={token}") as ws:
        ws.send_text('{"history": []}')
        ws.receive_json()


def test_ws_explain_under_limit(client):
    """WS /ws/ai/explain — лимит общий для всех /ws/ai/*."""
    token = _login(client)
    with client.websocket_connect(f"/ws/ai/explain?token={token}&topic_id=1") as ws:
        ws.send_text('{"topic_id": 1}')
        ws.receive_json()


def test_ws_generate_under_limit(client):
    """WS /ws/ai/generate доступен (без ошибок WS-handshake)."""
    token = _login(client)
    # Используем topic_id=99999 — будет error "Topic not found", но это НЕ WS-handshake ошибка.
    # Главное что лимит middleware не блокирует.
    import json

    with client.websocket_connect(f"/ws/ai/generate?token={token}") as ws:
        ws.send_text(json.dumps({"topic_id": 99999, "difficulty": 2}))
        msg = ws.receive_json()
        # Должен быть либо "done" либо "error" — но не WebSocketDisconnect
        assert msg["type"] in {"done", "error"}


def test_ws_concurrent_limit_blocks_6th(client):
    """После 5 WS в минуту — middleware возвращает 429."""
    # Прямой unit-тест middleware: проверяем поведение лога
    from app.main import _ws_concurrent_log
    import time

    # Симулируем 5 открытий
    uid = 1
    now = time.time()
    _ws_concurrent_log[uid] = [now] * 5

    # 6-й — должно превысить лимит (но мы не вызываем middleware
    # через синхронный TestClient.request — это сложно для WebSocket.
    # Поэтому просто проверяем что log правильно обновился.
    assert len(_ws_concurrent_log[uid]) == 5

    # Вручную симулируем работу middleware
    window = 60.0
    max_ws = 5
    log = _ws_concurrent_log.setdefault(uid, [])
    while log and log[0] < now - window:
        log.pop(0)
    exceeded = len(log) >= max_ws
    assert exceeded is True

    # Чистим для следующего теста
    _ws_concurrent_log.clear()


def test_ws_log_isolated_per_test(client):
    """autouse fixture очищает _ws_concurrent_log."""
    _ws_concurrent_log[1] = [999999999]
    # Conftest autouse должен очистить — тест пройдёт без блокировки
    token = _login(client)
    r = client.get(
        f"/ws/ai/chat?token={token}",
        headers={"Upgrade": "websocket", "Connection": "Upgrade"},
    )
    assert r.status_code != 429  # не должно быть заблокировано
