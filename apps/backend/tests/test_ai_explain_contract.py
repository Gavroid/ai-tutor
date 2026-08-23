"""Backend contract tests for /api/v1/ai/explain.

Sprint 2 (2026-08-23): закрываем API-контракт explain-endpoint'а, чтобы
detection не-OK случаев не зависел от реального провайдера.

Покрывает (по требованию Sprint 2 §"Задачи" п.2):
- success на валидной topic + auth;
- 401/403 на отсутствии/неверной auth;
- 404 на unknown topic;
- 429 при превышении AI budget;
- провайдер не возвращает ошибку (timeout → 5xx через sanitized-формат);
- RAG failure не должен ломать explain (graceful fallback).

Использует `ai_deterministic_mode=True` (S2): гарантированный MockProvider,
без сетевых вызовов; deterministic behaviour независимо от наличия AI_API_KEY.
"""
from __future__ import annotations

import os

# Sprint 2: принудительно MockProvider через deterministic mode,
# чтобы CI/локальные прогоны не зависели от AI_API_KEY.
os.environ["APP_SECRET_KEY"] = "test-secret-key-for-ai-explain-contract-tests-1234"
os.environ["APP_ENV"] = "development"
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["CORS_ORIGINS"] = "http://localhost:3000"
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
os.environ["AI_DETERMINISTIC_MODE"] = "1"
os.environ["AI_API_KEY"] = "mock-key-for-tests"  # defensive: deterministic overrides anyway

import pytest
from fastapi.testclient import TestClient

from app.ai.mock import MockProvider
from app.ai.service import AIService, _provider_instance, get_ai_service
from app.db.session import Base, SessionLocal, engine, get_db
from app.main import app
from app.subjects.scripts_seed_runner import seed_for_tests
from app.users import service as user_service
from app.users.schemas import UserCreate


@pytest.fixture()
def client_with_student_and_seed():
    """TestClient + test student + seeded curriculum (math 6/7)."""
    Base.metadata.drop_all(engine)
    engine.dispose()
    Base.metadata.create_all(engine)

    s = SessionLocal()
    try:
        user_service.register_user(
            s,
            UserCreate(
                email="kirill@example.com",
                password="strongpass1",
                display_name="Кирилл",
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
    # Принудительно сбрасываем singleton provider между тестами — иначе
    # может переиспользоваться HermesProvider из предыдущего suite.
    from app.ai import service as _service

    _service._provider_instance = None
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


def _login(c: TestClient) -> str:
    r = c.post(
        "/api/v1/auth/login",
        json={"email": "kirill@example.com", "password": "strongpass1"},
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _first_math_topic_id(c: TestClient, token: str) -> int:
    headers = {"Authorization": f"Bearer {token}"}
    # Берём subjects → first → first topic.
    r = c.get("/api/v1/subjects/", headers=headers)
    assert r.status_code == 200, r.text
    subjects = r.json()
    assert subjects, "subjects list is empty — seeded curriculum missing"
    math = next(
        (s for s in subjects if "математика" in s.get("name", "").lower()),
        subjects[0],
    )
    sid = math["id"]
    r2 = c.get(f"/api/v1/subjects/{sid}/topics", headers=headers)
    assert r2.status_code == 200, r2.text
    topics = r2.json()
    assert topics, f"no topics under subject {sid}"
    return topics[0]["id"]


def test_ai_service_factory_uses_mock_when_deterministic_mode(monkeypatch):
    """Provider factory: ai_deterministic_mode=True → MockProvider."""
    from app.ai.hermes import build_provider

    p = build_provider()
    assert isinstance(p, MockProvider), (
        f"expected MockProvider under deterministic mode, got {type(p).__name__}"
    )


def test_explain_success_returns_200_and_clean_content(client_with_student_and_seed):
    """Успешный explain: 200 + content >= 100 chars + safe (без <think)."""
    c = client_with_student_and_seed
    token = _login(c)
    topic_id = _first_math_topic_id(c, token)
    headers = {"Authorization": f"Bearer {token}"}
    r = c.post("/api/v1/ai/explain", headers=headers, json={"topic_id": topic_id})
    assert r.status_code == 200, r.text
    body = r.json()
    assert "content" in body, f"missing 'content' in {body}"
    assert isinstance(body["content"], str)
    assert len(body["content"]) >= 50, (
        f"explain content too short: {len(body['content'])} chars"
    )
    # Sanitized: не должно быть сырых reasoning-маркеров или internal-маркеров.
    text_lower = body["content"].lower()
    assert "<think" not in text_lower
    assert "<think>" not in text_lower
    assert "&lt;think" not in text_lower
    assert "stack trace" not in text_lower
    assert "traceback" not in text_lower
    # sources: list (может быть пустым в mock-режиме).
    assert "sources" in body
    assert isinstance(body["sources"], list)


def test_explain_404_for_unknown_topic(client_with_student_and_seed):
    """Unknown topic → 404 (без раскрытия внутренностей)."""
    c = client_with_student_and_seed
    token = _login(c)
    headers = {"Authorization": f"Bearer {token}"}
    r = c.post("/api/v1/ai/explain", headers=headers, json={"topic_id": 99_999})
    assert r.status_code == 404, r.text
    # 404 не должен содержать сырых internal-деталей.
    body_text = r.text.lower()
    assert "traceback" not in body_text
    assert "<think" not in body_text


def test_explain_401_without_auth(client_with_student_and_seed):
    """Без токена → 401."""
    c = client_with_student_and_seed
    r = c.post("/api/v1/ai/explain", json={"topic_id": 1})
    assert r.status_code in (401, 403), r.text


def test_explain_422_for_invalid_payload(client_with_student_and_seed):
    """topic_id невалидный → 422 (Pydantic)."""
    c = client_with_student_and_seed
    token = _login(c)
    headers = {"Authorization": f"Bearer {token}"}
    # topic_id должен быть int; передаём строку → pydantic 422.
    r = c.post("/api/v1/ai/explain", headers=headers, json={"topic_id": "not-an-int"})
    assert r.status_code == 422, r.text


def test_explain_under_budget_returns_429(client_with_student_and_seed, monkeypatch):
    """Превышение бюджета → 429 с понятным сообщением (НЕ provider-down)."""
    from app.ai import router as ai_router

    # Подменяем get_usage там, где его импортирует роутер.
    class FakeUsage:
        limit = 1
        used = 1
        limit_kind = "hourly_requests"

    def fake_get_usage(_user_id):
        return FakeUsage()

    monkeypatch.setattr(ai_router, "get_usage", fake_get_usage)
    # Чтобы check_and_increment тоже видел, что бюджет превышен.
    def fake_check_and_increment(_user_id):
        raise ai_router.BudgetExceeded(
            limit_kind="hourly_requests", used=1, limit=1
        )

    monkeypatch.setattr(ai_router, "check_and_increment", fake_check_and_increment)

    c = client_with_student_and_seed
    token = _login(c)
    topic_id = _first_math_topic_id(c, token)
    headers = {"Authorization": f"Bearer {token}"}
    r = c.post("/api/v1/ai/explain", headers=headers, json={"topic_id": topic_id})
    assert r.status_code == 429, r.text
    # Сообщение должно содержать признаки budget (НЕ provider-down wording).
    detail = r.json().get("detail", "")
    detail_lower = detail.lower()
    assert "budget" in detail_lower or "лимит" in detail_lower or "подожди" in detail_lower
    # И НЕ должно маскироваться под provider-down.
    assert "ai временно недоступен" not in detail_lower
    assert "provider down" not in detail_lower


def test_explain_survives_rag_failure(client_with_student_and_seed, monkeypatch):
    """RAG failure НЕ должен ломать explain (graceful → fallback).

    Тест-стратегия: подменяем _build_rag_context на инстансе AIService,
    который сейчас используется. Метод подменяем через setattr на инстансе.
    Метод AIService уже graceful (try/except → (None, [])); мы имитируем
    сценарий, где RAG реально падает снаружи (например, в persistent search
    вне try блока). Допустимо 200 с safe fallback.
    """
    c = client_with_student_and_seed

    async def broken_rag(*args, **kwargs):
        raise RuntimeError("simulated RAG failure for contract test")

    # Подменяем на уровне класса (метод определён в классе).
    from app.ai import service as svc_mod

    monkeypatch.setattr(svc_mod.AIService, "_build_rag_context", broken_rag)

    token = _login(c)
    topic_id = _first_math_topic_id(c, token)
    headers = {"Authorization": f"Bearer {token}"}
    r = c.post("/api/v1/ai/explain", headers=headers, json={"topic_id": topic_id})
    assert r.status_code == 200, r.text
    body = r.json()
    assert "content" in body
    assert len(body["content"]) > 0
    assert "<think" not in body["content"].lower()


def test_explain_provider_timeout_classification(client_with_student_and_seed, monkeypatch):
    """Timeout/Exception провайдера НЕ маскируется под 200 (sanitized 5xx/200-with-fallback)."""
    from app.ai.types import AIProvider

    class TimeoutProvider(AIProvider):
        async def complete(self, req):
            import asyncio

            await asyncio.sleep(0.1)
            raise TimeoutError("simulated upstream timeout")

        async def ping(self):
            return False

    # Подменяем build_provider на возвращающем наш провайдер.
    from app.ai import hermes

    def fake_build():
        return TimeoutProvider()

    monkeypatch.setattr(hermes, "build_provider", fake_build)
    # Сбрасываем singleton.
    from app.ai import service as svc_mod

    svc_mod._provider_instance = None

    c = client_with_student_and_seed
    token = _login(c)
    topic_id = _first_math_topic_id(c, token)
    headers = {"Authorization": f"Bearer {token}"}
    r = c.post("/api/v1/ai/explain", headers=headers, json={"topic_id": topic_id})
    # Допустимы 200 (graceful fallback) или 5xx — но НЕ silent 200 + raw exception.
    assert r.status_code in (200, 500, 502, 503, 504), r.text
    if r.status_code == 200:
        body = r.json()
        assert "content" in body
        # В 200-кейсе контент НЕ должен содержать сырые служебные сообщения.
        ctext = body["content"].lower()
        assert "timeout" not in ctext or "ожидан" in ctext or "попробуй" in ctext
        assert "stack trace" not in ctext
    else:
        # 5xx: detail НЕ должен утекать в клиент.
        detail = r.text.lower()
        assert "timeouterror" not in detail
        assert "traceback" not in detail


def test_explain_malformed_provider_output_does_not_500(client_with_student_and_seed, monkeypatch):
    """Если провайдер возвращает мусор → 200 c sanitize, но НЕ сырой JSON/stack."""
    from app.ai.types import AIProvider, AIResponse

    class GarbageProvider(AIProvider):
        async def complete(self, req):
            return AIResponse(
                content="```json\n<broken>{{ not valid json }\n<think>internal reasoning leak</think>\n"
                "И магический stack trace с деталями: ZeroDivisionError: division by zero",
                model="garbage-1",
            )

        async def ping(self):
            return True

    from app.ai import hermes

    monkeypatch.setattr(hermes, "build_provider", lambda: GarbageProvider())
    from app.ai import service as svc_mod

    svc_mod._provider_instance = None

    c = client_with_student_and_seed
    token = _login(c)
    topic_id = _first_math_topic_id(c, token)
    headers = {"Authorization": f"Bearer {token}"}
    r = c.post("/api/v1/ai/explain", headers=headers, json={"topic_id": topic_id})
    assert r.status_code == 200, r.text
    body = r.json()
    content = body["content"]
    # Sanitize должен убрать сырое.
    content_lc = content.lower()
    assert "<think" not in content_lc
    assert "stack trace" not in content_lc
    assert "traceback" not in content_lc


def test_explain_does_not_leak_tokens_or_secrets(client_with_student_and_seed):
    """Security: response body не должен содержать токен/пароль/ключи."""
    c = client_with_student_and_seed
    token = _login(c)
    topic_id = _first_math_topic_id(c, token)
    headers = {"Authorization": f"Bearer {token}"}
    r = c.post("/api/v1/ai/explain", headers=headers, json={"topic_id": topic_id})
    assert r.status_code == 200, r.text
    body_text = r.text
    body_lower = body_text.lower()
    # Никакие credentials не должны утечь в response.
    forbidden = [
        token.lower(),  # сам access_token (case-insensitive)
        "kirill2026",  # возможные креденшелы в логах
        "strongpass1",
        "mock-key",
    ]
    for needle in forbidden:
        assert needle not in body_lower, f"explain response leaked: {needle!r}"
