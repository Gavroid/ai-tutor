"""Sprint 3.9.6 — Тесты мульти-провайдера AI.

Покрывает:
1. CRUD провайдеров (create / list / get / update / delete).
2. Шифрование API-ключа (encrypt → decrypt = same, last4 корректный).
3. Fetch моделей с провайдера (mock httpx) — добавляет новые, идемпотентность.
4. Toggle is_active модели.
5. Назначение моделей на предмет (primary / fallback).
6. resolve_provider_for_subject — корректный выбор.
7. resolve_provider_for_subject — fallback если primary failed.
8. Subject routing: 404 на несуществующий предмет / модель.
9. Non-admin получает 403.
"""
from __future__ import annotations

import os

os.environ["APP_SECRET_KEY"] = "test-secret-key-for-pytest-only-1234567890"
os.environ["APP_ENV"] = "development"
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["CORS_ORIGINS"] = "http://localhost:3000"
os.environ["AI_API_KEY"] = "mock-key-for-tests"

from unittest.mock import AsyncMock, patch

import pytest
from app.admin import ai_providers as prov_models
from app.admin import ai_providers_service as prov_service
from app.auth.security import hash_password
from app.db.session import Base, SessionLocal, engine, get_db
from app.main import app
from app.subjects import models as subj_models
from app.users import service as user_service
from app.users.models import Role as UserRole
from app.users.models import User
from app.users.schemas import UserCreate
from fastapi.testclient import TestClient


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    engine.dispose()
    Base.metadata.create_all(engine)

    s = SessionLocal()
    try:
        admin = User(
            email="admin@example.com",
            password_hash=hash_password("strongpass1"),
            display_name="Admin",
            role=UserRole.ADMIN,
        )
        s.add(admin)

        student = user_service.register_user(
            s,
            UserCreate(
                email="kid@example.com",
                password="strongpass1",
                display_name="Кирилл",
                role="student",
                grade=7,
            ),
        )
        # Создадим Subject для тестов маршрутизации.
        sub = subj_models.Subject(
            code="physics",
            name="Физика",
            recommended_grade=7,
        )
        s.add(sub)
        s.commit()
        s.refresh(sub)
        s.refresh(admin)
        s.refresh(student)
    finally:
        s.close()

    yield TestClient(app)
    Base.metadata.drop_all(engine)
    engine.dispose()


def _login(client: TestClient, email: str, password: str) -> str:
    r = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ---------- 1. Encryption ----------

def test_encryption_roundtrip():
    enc = prov_service.encrypt_api_key("sk-or-test-1234567890abcdef")
    assert isinstance(enc, bytes)
    assert prov_service.decrypt_api_key(enc) == "sk-or-test-1234567890abcdef"


def test_api_key_last4():
    enc = prov_service.encrypt_api_key("sk-or-v1-1234567890abcdef")
    last4 = prov_service.api_key_last4(enc)
    assert last4.endswith("cdef")
    assert last4.startswith("•")


# ---------- 2. CRUD ----------

def test_create_and_list_provider(client: TestClient):
    token = _login(client, "admin@example.com", "strongpass1")
    # Create.
    r = client.post(
        "/api/v1/admin/ai-providers",
        headers=_auth(token),
        json={
            "name": "OpenRouter основной",
            "kind": "openai_compat",
            "base_url": "https://openrouter.ai/api/v1",
            "api_key": "sk-or-v1-1234567890abcdef",
        },
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["name"] == "OpenRouter основной"
    assert data["api_key_last4"].endswith("cdef")
    assert "api_key_encrypted" not in data  # Безопасность: ключ не отдаётся.

    # List.
    r = client.get("/api/v1/admin/ai-providers", headers=_auth(token))
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 1
    assert items[0]["id"] == data["id"]
    assert items[0]["models_count"] == 0


def test_create_provider_unique_name(client: TestClient):
    token = _login(client, "admin@example.com", "strongpass1")
    payload = {
        "name": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "api_key": "sk-or-test-12345",
    }
    r1 = client.post("/api/v1/admin/ai-providers", headers=_auth(token), json=payload)
    assert r1.status_code == 201
    r2 = client.post("/api/v1/admin/ai-providers", headers=_auth(token), json=payload)
    assert r2.status_code == 409
    assert "уже существует" in r2.text


def test_update_provider(client: TestClient):
    token = _login(client, "admin@example.com", "strongpass1")
    r = client.post(
        "/api/v1/admin/ai-providers",
        headers=_auth(token),
        json={
            "name": "Provider 1",
            "base_url": "https://api.example.com/v1",
            "api_key": "key-12345678",
        },
    )
    pid = r.json()["id"]

    # Update note + is_active.
    r = client.patch(
        f"/api/v1/admin/ai-providers/{pid}",
        headers=_auth(token),
        json={"is_active": False, "note": "test"},
    )
    assert r.status_code == 200
    assert r.json()["is_active"] is False
    assert r.json()["note"] == "test"

    # Update api_key — last4 должен смениться.
    r = client.patch(
        f"/api/v1/admin/ai-providers/{pid}",
        headers=_auth(token),
        json={"api_key": "new-key-9999"},
    )
    assert r.status_code == 200
    assert r.json()["api_key_last4"].endswith("9999")


def test_delete_provider(client: TestClient):
    token = _login(client, "admin@example.com", "strongpass1")
    r = client.post(
        "/api/v1/admin/ai-providers",
        headers=_auth(token),
        json={
            "name": "P",
            "base_url": "https://x.com/v1",
            "api_key": "kkkk-1234",
        },
    )
    pid = r.json()["id"]
    r = client.delete(f"/api/v1/admin/ai-providers/{pid}", headers=_auth(token))
    assert r.status_code == 204
    r = client.get(f"/api/v1/admin/ai-providers/{pid}", headers=_auth(token))
    assert r.status_code == 404


# ---------- 3. Fetch models ----------

@pytest.mark.asyncio
async def test_fetch_models_creates_catalog(client: TestClient):
    token = _login(client, "admin@example.com", "strongpass1")
    r = client.post(
        "/api/v1/admin/ai-providers",
        headers=_auth(token),
        json={
            "name": "Mock provider",
            "base_url": "https://api.test/v1",
            "api_key": "kkkk-1234",
        },
    )
    pid = r.json()["id"]

    # Mock httpx response.
    fake_resp = type("R", (), {
        "status_code": 200,
        "json": lambda self: {"data": [{"id": "model-a"}, {"id": "model-b"}, {"id": "model-c"}]},
        "text": "{}",
    })()

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def get(self, *a, **kw): return fake_resp

    with patch("app.admin.ai_providers_service.httpx.AsyncClient", FakeAsyncClient):
        r = client.post(f"/api/v1/admin/ai-providers/{pid}/fetch", headers=_auth(token))

    assert r.status_code == 200, r.text
    data = r.json()
    assert data["total_fetched"] == 3
    assert data["added"] == 3
    assert data["already_present"] == 0
    assert len(data["models"]) == 3

    # Второй fetch должен быть идемпотентным.
    with patch("app.admin.ai_providers_service.httpx.AsyncClient", FakeAsyncClient):
        r = client.post(f"/api/v1/admin/ai-providers/{pid}/fetch", headers=_auth(token))
    assert r.json()["added"] == 0
    assert r.json()["already_present"] == 3


@pytest.mark.asyncio
async def test_test_provider_connection_ok(client: TestClient):
    token = _login(client, "admin@example.com", "strongpass1")
    r = client.post(
        "/api/v1/admin/ai-providers",
        headers=_auth(token),
        json={"name": "P", "base_url": "https://x.com/v1", "api_key": "k1234"},
    )
    pid = r.json()["id"]

    fake_resp = type("R", (), {"status_code": 200, "json": lambda self: {"data": [{"id": "m1"}]}, "text": "{}"})()
    class FakeAC:
        def __init__(self, *a, **kw): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def get(self, *a, **kw): return fake_resp

    with patch("app.admin.ai_providers_service.httpx.AsyncClient", FakeAC):
        r = client.post(f"/api/v1/admin/ai-providers/{pid}/test", headers=_auth(token))
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["status_code"] == 200
    assert data["models_count"] == 1
    assert data["latency_ms"] is not None


@pytest.mark.asyncio
async def test_test_provider_connection_fail(client: TestClient):
    token = _login(client, "admin@example.com", "strongpass1")
    r = client.post(
        "/api/v1/admin/ai-providers",
        headers=_auth(token),
        json={"name": "BadP", "base_url": "https://x.com/v1", "api_key": "wrong-key"},
    )
    pid = r.json()["id"]

    fake_resp = type("R", (), {"status_code": 401, "json": lambda self: {}, "text": "Unauthorized"})()
    class FakeAC:
        def __init__(self, *a, **kw): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def get(self, *a, **kw): return fake_resp

    with patch("app.admin.ai_providers_service.httpx.AsyncClient", FakeAC):
        r = client.post(f"/api/v1/admin/ai-providers/{pid}/test", headers=_auth(token))
    assert r.status_code == 200  # 200 потому что endpoint возвращает результат теста, не провайдера.
    data = r.json()
    assert data["ok"] is False
    assert data["status_code"] == 401


# ---------- 4. Toggle model ----------

def test_toggle_model(client: TestClient):
    token = _login(client, "admin@example.com", "strongpass1")
    s = SessionLocal()
    try:
        # Создаём провайдера и модель напрямую через сервис.
        from app.admin.ai_providers_service import create_provider
        provider = create_provider(
            s,
            name="P",
            kind="openai_compat",
            base_url="https://x.com/v1",
            api_key="kkkk-1234",
            is_active=True,
            note=None,
        )
        from app.admin.ai_providers import AIModelCatalog
        m = AIModelCatalog(provider_id=provider.id, model_name="model-x", is_active=False)
        s.add(m)
        s.commit()
        s.refresh(m)
        mid = m.id
    finally:
        s.close()

    r = client.patch(f"/api/v1/admin/ai-models/{mid}", headers=_auth(token), json={"is_active": True})
    assert r.status_code == 200
    assert r.json()["is_active"] is True


# ---------- 5. Subject assignment ----------

def test_assign_models_to_subject(client: TestClient):
    token = _login(client, "admin@example.com", "strongpass1")
    s = SessionLocal()
    try:
        from app.admin.ai_providers_service import create_provider
        prov1 = create_provider(
            s, name="P1", kind="openai_compat",
            base_url="https://x.com/v1", api_key="key-12345", is_active=True, note=None,
        )
        prov2 = create_provider(
            s, name="P2", kind="openai_compat",
            base_url="https://y.com/v1", api_key="key-67890", is_active=True, note=None,
        )
        from app.admin.ai_providers import AIModelCatalog
        m1 = AIModelCatalog(provider_id=prov1.id, model_name="model-A", is_active=True)
        m2 = AIModelCatalog(provider_id=prov2.id, model_name="model-B", is_active=True)
        s.add_all([m1, m2])
        s.commit()
        s.refresh(m1)
        s.refresh(m2)
        m1_id, m2_id = m1.id, m2.id

        subject = s.query(subj_models.Subject).filter(subj_models.Subject.code == "physics").one()
        sid = subject.id
    finally:
        s.close()

    # Назначаем primary.
    r = client.put(
        f"/api/v1/admin/subjects/{sid}/ai-assignment",
        headers=_auth(token),
        json={"primary": m1_id},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["primary"]["model_name"] == "model-A"
    assert data["fallback"] is None

    # Назначаем fallback.
    r = client.put(
        f"/api/v1/admin/subjects/{sid}/ai-assignment",
        headers=_auth(token),
        json={"fallback": m2_id},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["primary"]["model_name"] == "model-A"
    assert data["fallback"]["model_name"] == "model-B"

    # Get.
    r = client.get(f"/api/v1/admin/subjects/{sid}/ai-assignment", headers=_auth(token))
    assert r.status_code == 200
    data = r.json()
    assert data["primary"]["model_name"] == "model-A"
    assert data["fallback"]["model_name"] == "model-B"


def test_clear_primary_with_zero(client: TestClient):
    token = _login(client, "admin@example.com", "strongpass1")
    s = SessionLocal()
    try:
        from app.admin.ai_providers_service import create_provider
        prov = create_provider(
            s, name="P", kind="openai_compat",
            base_url="https://x.com/v1", api_key="key-12345", is_active=True, note=None,
        )
        from app.admin.ai_providers import AIModelCatalog
        m = AIModelCatalog(provider_id=prov.id, model_name="model-X", is_active=True)
        s.add(m)
        s.commit()
        s.refresh(m)
        mid = m.id
        subject = s.query(subj_models.Subject).filter(subj_models.Subject.code == "physics").one()
        sid = subject.id
    finally:
        s.close()

    # Назначаем.
    client.put(f"/api/v1/admin/subjects/{sid}/ai-assignment", headers=_auth(token), json={"primary": mid})
    # Чистим (primary=0 → clear).
    r = client.put(
        f"/api/v1/admin/subjects/{sid}/ai-assignment",
        headers=_auth(token),
        json={"primary": 0},
    )
    assert r.status_code == 200
    assert r.json()["primary"] is None


# ---------- 6. Resolve provider for subject ----------

def test_resolve_provider_for_subject_returns_config(client: TestClient):
    s = SessionLocal()
    try:
        from app.admin.ai_providers_service import (
            assign_model_to_subject,
            create_provider,
            resolve_provider_for_subject,
        )
        prov = create_provider(
            s, name="OpenRouter", kind="openai_compat",
            base_url="https://openrouter.ai/api/v1",
            api_key="sk-or-v1-test-12345678",
            is_active=True, note=None,
        )
        from app.admin.ai_providers import AIModelCatalog
        m = AIModelCatalog(provider_id=prov.id, model_name="gpt-test", is_active=True)
        s.add(m)
        s.commit()
        s.refresh(m)
        subj = s.query(subj_models.Subject).filter(subj_models.Subject.code == "physics").one()
        assign_model_to_subject(s, subj.id, model_id=m.id, role="primary")

        cfg = resolve_provider_for_subject(s, subj.id)
        assert cfg is not None
        assert cfg["provider_name"] == "OpenRouter"
        assert cfg["model_name"] == "gpt-test"
        assert cfg["api_key"] == "sk-or-v1-test-12345678"  # расшифровано.
        assert cfg["base_url"] == "https://openrouter.ai/api/v1"
    finally:
        s.close()


def test_resolve_provider_returns_none_if_not_configured(client: TestClient):
    s = SessionLocal()
    try:
        from app.admin.ai_providers_service import resolve_provider_for_subject
        subj = s.query(subj_models.Subject).filter(subj_models.Subject.code == "physics").one()
        cfg = resolve_provider_for_subject(s, subj.id)
        assert cfg is None  # Не настроено — fallback на default.
    finally:
        s.close()


def test_resolve_provider_returns_none_if_inactive(client: TestClient):
    s = SessionLocal()
    try:
        from app.admin.ai_providers_service import (
            assign_model_to_subject,
            create_provider,
            resolve_provider_for_subject,
        )
        prov = create_provider(
            s, name="Disabled", kind="openai_compat",
            base_url="https://x.com/v1", api_key="k1234567",
            is_active=False, note=None,  # Неактивный провайдер.
        )
        from app.admin.ai_providers import AIModelCatalog
        m = AIModelCatalog(provider_id=prov.id, model_name="m1", is_active=True)
        s.add(m)
        s.commit()
        s.refresh(m)
        subj = s.query(subj_models.Subject).filter(subj_models.Subject.code == "physics").one()
        assign_model_to_subject(s, subj.id, model_id=m.id, role="primary")
        cfg = resolve_provider_for_subject(s, subj.id)
        assert cfg is None  # Неактивный провайдер → None → default.
    finally:
        s.close()


# ---------- 7. AIService._complete_with_fallback flow ----------

@pytest.mark.asyncio
async def test_complete_with_fallback_primary_ok(client: TestClient):
    s = SessionLocal()
    try:
        from app.admin.ai_providers_service import (
            assign_model_to_subject,
            create_provider,
        )
        from app.ai.types import AIRequest, AIResponse

        prov = create_provider(
            s, name="P1", kind="openai_compat",
            base_url="https://x.com/v1", api_key="kkkk-1234",
            is_active=True, note=None,
        )
        from app.admin.ai_providers import AIModelCatalog
        m = AIModelCatalog(provider_id=prov.id, model_name="model-A", is_active=True)
        s.add(m)
        s.commit()
        s.refresh(m)
        subj = s.query(subj_models.Subject).filter(subj_models.Subject.code == "physics").one()
        assign_model_to_subject(s, subj.id, model_id=m.id, role="primary")

        # Создаём AIService с default provider (mock).
        from app.ai.mock import MockProvider
        from app.ai.service import AIService
        svc = AIService(MockProvider())

        # Mock primary provider's complete.
        good_resp = AIResponse(content="primary says hi", model="model-A")
        with patch(
            "app.ai.service.HermesProvider.complete",
            AsyncMock(return_value=good_resp),
        ):
            req = AIRequest(messages=[], mode="test")
            resp, label = await svc._complete_with_fallback(s, subj.id, req)
        assert resp.content == "primary says hi"
        assert label.startswith("subject:")
        assert "model-A" in label
    finally:
        s.close()


@pytest.mark.asyncio
async def test_complete_with_fallback_primary_fails_fallback_ok(client: TestClient):
    s = SessionLocal()
    try:
        from app.admin.ai_providers_service import (
            assign_model_to_subject,
            create_provider,
        )
        from app.ai.types import AIRequest, AIResponse

        prov1 = create_provider(
            s, name="Primary", kind="openai_compat",
            base_url="https://primary.com/v1", api_key="primary-key",
            is_active=True, note=None,
        )
        prov2 = create_provider(
            s, name="Fallback", kind="openai_compat",
            base_url="https://fallback.com/v1", api_key="fallback-key",
            is_active=True, note=None,
        )
        from app.admin.ai_providers import AIModelCatalog
        m1 = AIModelCatalog(provider_id=prov1.id, model_name="primary-model", is_active=True)
        m2 = AIModelCatalog(provider_id=prov2.id, model_name="fallback-model", is_active=True)
        s.add_all([m1, m2])
        s.commit()
        s.refresh(m1)
        s.refresh(m2)
        subj = s.query(subj_models.Subject).filter(subj_models.Subject.code == "physics").one()
        assign_model_to_subject(s, subj.id, model_id=m1.id, role="primary")
        assign_model_to_subject(s, subj.id, model_id=m2.id, role="fallback")

        from app.ai.mock import MockProvider
        from app.ai.service import AIService
        svc = AIService(MockProvider())

        # Primary fails, fallback succeeds.
        fb_resp = AIResponse(content="fallback saved the day", model="fallback-model")

        async def maybe_complete(self, req):
            # Если base_url содержит "primary" — fail, иначе OK.
            if "primary.com" in self.base_url:
                raise RuntimeError("primary failed")
            return fb_resp

        with patch("app.ai.service.HermesProvider.complete", maybe_complete):
            req = AIRequest(messages=[], mode="test")
            resp, label = await svc._complete_with_fallback(s, subj.id, req)
        assert resp.content == "fallback saved the day"
        assert label.startswith("fallback:")
    finally:
        s.close()


@pytest.mark.asyncio
async def test_complete_with_no_subject_falls_back_to_default(client: TestClient):
    """Без subject_id — используется env default provider."""
    from app.ai.mock import MockProvider
    from app.ai.service import AIService
    from app.ai.types import AIRequest

    s = SessionLocal()
    try:
        svc = AIService(MockProvider())
        req = AIRequest(messages=[], mode="test")
        resp, label = await svc._complete_with_fallback(s, None, req)
        assert label == "default"
    finally:
        s.close()


# ---------- 8. Auth: non-admin gets 403 ----------

def test_non_admin_cannot_access_ai_providers(client: TestClient):
    token = _login(client, "kid@example.com", "strongpass1")
    r = client.get("/api/v1/admin/ai-providers", headers=_auth(token))
    assert r.status_code == 403


def test_anonymous_cannot_access_ai_providers(client: TestClient):
    r = client.get("/api/v1/admin/ai-providers")
    assert r.status_code == 401


# ---------- 9. Edge cases ----------

def test_assign_to_nonexistent_subject(client: TestClient):
    token = _login(client, "admin@example.com", "strongpass1")
    r = client.put(
        "/api/v1/admin/subjects/999999/ai-assignment",
        headers=_auth(token),
        json={"primary": 1},
    )
    assert r.status_code == 404


def test_assign_nonexistent_model(client: TestClient):
    token = _login(client, "admin@example.com", "strongpass1")
    s = SessionLocal()
    try:
        subj = s.query(subj_models.Subject).filter(subj_models.Subject.code == "physics").one()
        sid = subj.id
    finally:
        s.close()
    r = client.put(
        f"/api/v1/admin/subjects/{sid}/ai-assignment",
        headers=_auth(token),
        json={"primary": 999999},
    )
    assert r.status_code == 404


def test_get_nonexistent_provider(client: TestClient):
    token = _login(client, "admin@example.com", "strongpass1")
    r = client.get("/api/v1/admin/ai-providers/999999", headers=_auth(token))
    assert r.status_code == 404
