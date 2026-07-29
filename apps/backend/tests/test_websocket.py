"""Тесты WebSocket для AI-чата (Этап UX).

Sprint 66: все тесты используют cookie auth (не query string).
Sprint 16.1 P1-2 ввёл cookie-based auth для WS, Sprint 66 удалил
query string fallback полностью.
"""
from __future__ import annotations

import os

os.environ["APP_SECRET_KEY"] = "test-secret-key-for-pytest-only-1234567890"
os.environ["APP_ENV"] = "development"
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["CORS_ORIGINS"] = "http://localhost:3000"
os.environ["AI_API_KEY"] = "mock-key-for-tests"

import json

import pytest
from fastapi.testclient import TestClient

from app.auth.security import ACCESS_COOKIE, create_access_token
from app.db.session import Base, SessionLocal, engine, get_db
from app.main import app
from app.subjects.scripts_seed_runner import seed_for_tests
from app.users import service as user_service
from app.users.schemas import UserCreate


@pytest.fixture()
def setup():
    Base.metadata.drop_all(engine)
    engine.dispose()
    Base.metadata.create_all(engine)

    s = SessionLocal()
    try:
        user_service.register_user(
            s,
            UserCreate(
                email="ws@example.com",
                password="strongpass1",
                display_name="WS User",
                role="student",
                grade=7,
            ),
        )
        seed_for_tests(s, reset=False)
    finally:
        s.close()

    def _gen():
        s = SessionLocal()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = _gen
    yield
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


def _token() -> str:
    """Sprint 66: get JWT для cookie auth."""
    s = SessionLocal()
    try:
        from app.users import models as user_models

        u = s.scalar(
            __import__("sqlalchemy").select(user_models.User).where(user_models.User.email == "ws@example.com")
        )
        result = create_access_token(u)
        return result.access_token if hasattr(result, "access_token") else result[0]
    finally:
        s.close()


@pytest.fixture
def client_with_cookie():
    """TestClient with login cookie set."""
    client = TestClient(app)
    token = _token()
    # Устанавливаем cookie через .cookies
    client.cookies.set(ACCESS_COOKIE, token)
    return client


def test_websocket_rejects_missing_token(setup):
    """Sprint 66: без cookie (и без query) → WS close."""
    client = TestClient(app)
    with pytest.raises(Exception):
        with client.websocket_connect("/ws/ai/chat") as ws:
            pass


def test_websocket_rejects_query_string_token(setup):
    """Sprint 66: query string ?token= → REJECTED (security fix)."""
    client = TestClient(app)
    token = _token()
    with pytest.raises(Exception):
        # Sprint 66: ?token= больше не работает — нужно cookie
        with client.websocket_connect(f"/ws/ai/chat?token={token}") as ws:
            pass


def test_websocket_chat_streams_chunks(setup):
    """Sprint 66: WS chat через cookie auth."""
    client = TestClient(app)
    token = _token()
    client.cookies.set(ACCESS_COOKIE, token)
    with client.websocket_connect("/ws/ai/chat") as ws:
        ws.send_text(json.dumps({"history": [{"role": "user", "content": "Привет"}], "topic_id": None}))
        chunks = []
        while True:
            msg = ws.receive_json()
            if msg["type"] == "chunk":
                chunks.append(msg["content"])
            elif msg["type"] == "done":
                break
            elif msg["type"] == "error":
                pytest.fail(f"WS error: {msg['message']}")
        assert "".join(chunks), "No chunks received"
        assert len(chunks) >= 1


def test_websocket_explain_streams(setup):
    """Sprint 66: WS explain через cookie auth."""
    client = TestClient(app)
    token = _token()
    s = SessionLocal()
    try:
        from app.subjects import models as subj_models

        topic = s.scalar(
            __import__("sqlalchemy").select(subj_models.Topic).limit(1)
        )
        tid = topic.id
    finally:
        s.close()

    client.cookies.set(ACCESS_COOKIE, token)
    with client.websocket_connect("/ws/ai/explain") as ws:
        ws.send_text(json.dumps({"topic_id": tid}))
        chunks = []
        while True:
            msg = ws.receive_json()
            if msg["type"] == "chunk":
                chunks.append(msg["content"])
            elif msg["type"] == "done":
                break
        assert "".join(chunks)


def test_websocket_generate_streams(setup):
    """Sprint 66: WS generate через cookie auth."""
    client = TestClient(app)
    token = _token()
    s = SessionLocal()
    try:
        from app.subjects import models as subj_models

        topic = s.scalar(
            __import__("sqlalchemy").select(subj_models.Topic).limit(1)
        )
        tid = topic.id
    finally:
        s.close()

    client.cookies.set(ACCESS_COOKIE, token)
    with client.websocket_connect("/ws/ai/generate") as ws:
        ws.send_text(json.dumps({"topic_id": tid, "difficulty": 2}))
        msg = ws.receive_json()
        assert msg["type"] == "done"
        assert "exercise" in msg
        ex = msg["exercise"]
        assert "question_text" in ex
        assert ex["type"] in {"single", "multiple", "numeric", "text", "fill", "code"}


def test_websocket_rejects_bad_token(setup):
    """Sprint 66: bad cookie token → WS close."""
    client = TestClient(app)
    client.cookies.set(ACCESS_COOKIE, "invalid_token_garbage")
    with pytest.raises(Exception):
        with client.websocket_connect("/ws/ai/chat") as ws:
            pass
