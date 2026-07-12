"""Тесты WebSocket для AI-чата (Этап UX)."""
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

from app.auth.security import create_access_token
from app.db.session import Base, SessionLocal, engine, get_db
from app.main import app
from app.subjects.scripts_seed_runner import seed_for_tests
from app.users import service as user_service
from app.users.schemas import UserCreate
from app.users.models import Role


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
    s = SessionLocal()
    try:
        from app.users import models as user_models

        u = s.scalar(
            __import__("sqlalchemy").select(user_models.User).where(user_models.User.email == "ws@example.com")
        )
        return create_access_token(u).access_token if hasattr(create_access_token(u), "access_token") else create_access_token(u)[0]
    finally:
        s.close()


def test_websocket_rejects_missing_token(setup):
    client = TestClient(app)
    with pytest.raises(Exception):
        with client.websocket_connect("/ws/ai/chat") as ws:
            pass


def test_websocket_chat_streams_chunks(setup):
    client = TestClient(app)
    token = _token()
    with client.websocket_connect(f"/ws/ai/chat?token={token}") as ws:
        ws.send_text(json.dumps({"history": [{"role": "user", "content": "Привет"}], "topic_id": None}))
        chunks = []
        # Читаем chunks, пока не придёт "done"
        while True:
            msg = ws.receive_json()
            if msg["type"] == "chunk":
                chunks.append(msg["content"])
            elif msg["type"] == "done":
                break
            elif msg["type"] == "error":
                pytest.fail(f"WS error: {msg['message']}")
        # Mock-ответ из test_ai.py должен быть стримен по частям
        assert "".join(chunks), "No chunks received"
        assert len(chunks) >= 1


def test_websocket_explain_streams(setup):
    client = TestClient(app)
    token = _token()
    # Находим тему
    s = SessionLocal()
    try:
        from app.subjects import models as subj_models

        topic = s.scalar(
            __import__("sqlalchemy").select(subj_models.Topic).limit(1)
        )
        tid = topic.id
    finally:
        s.close()

    with client.websocket_connect(f"/ws/ai/explain?token={token}") as ws:
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

    with client.websocket_connect(f"/ws/ai/generate?token={token}") as ws:
        ws.send_text(json.dumps({"topic_id": tid, "difficulty": 2}))
        msg = ws.receive_json()
        assert msg["type"] == "done"
        assert "exercise" in msg
        ex = msg["exercise"]
        assert "question_text" in ex
        assert ex["type"] in {"single", "multiple", "numeric", "text", "fill", "code"}


def test_websocket_rejects_bad_token(setup):
    client = TestClient(app)
    with pytest.raises(Exception):
        with client.websocket_connect("/ws/ai/chat?token=invalid") as ws:
            pass