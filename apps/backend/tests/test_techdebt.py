"""Sprint 4 — тесты технического долга: rate limit register, XFF trust."""
from __future__ import annotations

import json
import os

os.environ["APP_SECRET_KEY"] = "test-secret-key-for-pytest-only-1234567890"
os.environ["APP_ENV"] = "development"
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["CORS_ORIGINS"] = "http://localhost:3000"
os.environ["AI_API_KEY"] = "mock-key-for-tests"

import pytest
from fastapi.testclient import TestClient

from app.db.session import Base, SessionLocal, engine, get_db
from app.main import app, _client_ip, _ip_in_cidrs


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    engine.dispose()
    Base.metadata.create_all(engine)

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


# ============================================================
# _ip_in_cidrs helper
# ============================================================


def test_ip_in_cidrs_loopback():
    assert _ip_in_cidrs("127.0.0.1", ["127.0.0.1/32"]) is True


def test_ip_in_cidrs_private():
    assert _ip_in_cidrs("192.168.1.10", ["192.168.0.0/16"]) is True
    assert _ip_in_cidrs("10.0.0.5", ["10.0.0.0/8"]) is True
    assert _ip_in_cidrs("172.16.0.1", ["172.16.0.0/12"]) is True


def test_ip_in_cidrs_public_rejected():
    assert _ip_in_cidrs("8.8.8.8", ["192.168.0.0/16"]) is False
    assert _ip_in_cidrs("1.1.1.1", ["127.0.0.1/32"]) is False


def test_ip_in_cidrs_invalid_input():
    # Мусор не падает, просто False
    assert _ip_in_cidrs("not-an-ip", ["127.0.0.1/32"]) is False
    assert _ip_in_cidrs("127.0.0.1", ["invalid-cidr"]) is False


# ============================================================
# _client_ip helper
# ============================================================


class _FakeRequest:
    def __init__(self, host, headers=None):
        self.client = type("C", (), {"host": host})()
        self.headers = headers or {}


def test_client_ip_no_proxy_returns_host():
    """Без trusted_proxies — возвращается реальный host."""
    req = _FakeRequest("8.8.8.8")
    assert _client_ip(req, []) == "8.8.8.8"


def test_client_ip_trusted_proxy_uses_xff():
    """Если peer (request.client.host) — trusted, читаем X-Forwarded-For."""
    req = _FakeRequest("127.0.0.1", {"x-forwarded-for": "203.0.113.42, 10.0.0.1"})
    ip = _client_ip(req, ["127.0.0.1/32"])
    # Берём самый левый XFF
    assert ip == "203.0.113.42"


def test_client_ip_untrusted_peer_ignores_xff():
    """Если peer НЕ trusted — XFF игнорируется (защита от подмены)."""
    req = _FakeRequest("8.8.8.8", {"x-forwarded-for": "1.2.3.4"})
    ip = _client_ip(req, ["127.0.0.1/32"])
    # Должен вернуться реальный peer (8.8.8.8), а не подделанный XFF
    assert ip == "8.8.8.8"


def test_client_ip_private_network_trusted():
    """Приватные сети — типичные trusted proxies."""
    req = _FakeRequest("192.168.1.10", {"x-forwarded-for": "203.0.113.42"})
    ip = _client_ip(req, ["192.168.0.0/16", "10.0.0.0/8"])
    assert ip == "203.0.113.42"


def test_client_ip_no_xff_returns_host():
    """Trusted proxy, но XFF нет — возвращаем peer."""
    req = _FakeRequest("127.0.0.1", {})
    ip = _client_ip(req, ["127.0.0.1/32"])
    assert ip == "127.0.0.1"


# ============================================================
# Rate limit на /auth/register (integration)
# ============================================================


def _reg_payload(idx: int) -> dict:
    return {
        "email": f"user{idx}@example.com",
        "password": "strongpass1",
        "display_name": f"User{idx}",
        "role": "student",
        "grade": 7,
    }


def test_register_succeeds_within_limit(client):
    """5 регистраций подряд — все успешны (лимит = 5)."""
    for i in range(5):
        r = client.post("/api/v1/auth/register", json=_reg_payload(i))
        assert r.status_code == 201, f"register #{i}: {r.status_code} {r.text}"


def test_register_blocked_after_5_attempts(client):
    """6-я регистрация в течение часа → 429."""
    for i in range(5):
        r = client.post("/api/v1/auth/register", json=_reg_payload(i))
        assert r.status_code == 201

    # 6-я попытка с того же IP (testclient = "testclient") → 429
    r = client.post("/api/v1/auth/register", json=_reg_payload(99))
    assert r.status_code == 429
    assert "регистрац" in r.text.lower() or "подождите" in r.text.lower()


def test_register_blocked_message_in_russian(client):
    for i in range(5):
        client.post("/api/v1/auth/register", json=_reg_payload(i))
    r = client.post("/api/v1/auth/register", json=_reg_payload(100))
    assert r.status_code == 429
    # Сообщение должно быть на русском (по требованию проекта)
    body = r.json()
    assert "detail" in body
    assert any(ord(c) >= 0x0400 for c in body["detail"])  # есть кириллица


# ============================================================
# Audit log retention (Sprint 4.2)
# ============================================================


def _create_admin(client) -> int:
    """Создаёт admin в БД напрямую, возвращает id."""
    from app.auth.security import hash_password
    from app.users.models import Role, User

    s = SessionLocal()
    try:
        existing = s.query(User).filter_by(email="admin@example.com").first()
        if existing:
            return existing.id
        admin = User(
            email="admin@example.com",
            password_hash=hash_password("strongpass1"),
            display_name="Admin",
            role=Role.ADMIN,
        )
        s.add(admin)
        s.commit()
        return admin.id
    finally:
        s.close()


def _admin_token(client) -> str:
    return client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "strongpass1"},
    ).json()["access_token"]


def test_purge_requires_admin(client):
    """Без admin → 403 (или 401 если не залогинен)."""
    r = client.post("/api/v1/admin/audit-log/purge")
    assert r.status_code in (401, 403)


def test_purge_deletes_old_logs(client):
    """Старые логи удаляются, свежие остаются."""
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import insert

    from app.admin.models import AuditLog

    admin_id = _create_admin(client)
    s = SessionLocal()
    try:
        old_dt = datetime.now(timezone.utc) - timedelta(days=100)
        new_dt = datetime.now(timezone.utc) - timedelta(days=10)
        s.execute(
            insert(AuditLog).values(
                user_id=admin_id, action="old.test", created_at=old_dt
            )
        )
        s.execute(
            insert(AuditLog).values(
                user_id=admin_id, action="new.test", created_at=new_dt
            )
        )
        s.commit()
    finally:
        s.close()

    admin = _admin_token(client)
    r = client.post(
        "/api/v1/admin/audit-log/purge?ttl_days=90",
        headers={"Authorization": f"Bearer {admin}"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["deleted_count"] >= 1
    assert body["ttl_days"] == 90

    # Проверяем, что остались только свежие
    s = SessionLocal()
    try:
        old_count = s.query(AuditLog).filter_by(action="old.test").count()
        new_count = s.query(AuditLog).filter_by(action="new.test").count()
        assert old_count == 0, "Старый лог должен быть удалён"
        assert new_count == 1, "Свежий лог должен остаться"
    finally:
        s.close()


def test_purge_empty(client):
    """Нет старых логов → 0 удалено, не падает."""
    _create_admin(client)
    admin = _admin_token(client)
    r = client.post(
        "/api/v1/admin/audit-log/purge?ttl_days=90",
        headers={"Authorization": f"Bearer {admin}"},
    )
    assert r.status_code == 200
    assert r.json()["deleted_count"] == 0


def test_purge_writes_audit_log(client):
    """Purge сам себя пишет в audit log (meta!)."""
    _create_admin(client)
    admin = _admin_token(client)
    r = client.post(
        "/api/v1/admin/audit-log/purge?ttl_days=30",
        headers={"Authorization": f"Bearer {admin}"},
    )
    assert r.status_code == 200

    r2 = client.get(
        "/api/v1/admin/audit-log?action=audit.purge",
        headers={"Authorization": f"Bearer {admin}"},
    )
    assert r2.status_code == 200
    events = r2.json()
    assert len(events) >= 1
    # details — JSON-строка в БД, парсим
    details = events[0]["details"]
    if isinstance(details, str):
        details = json.loads(details)
    assert details["ttl_days"] == 30
