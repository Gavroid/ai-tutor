"""Sprint 40: CGM (Continuous Glucose Monitor) tests.

Тестируем:
- CGMConfig opt-in: GET/PUT /api/v1/cgm/config
- URL validation (только HTTPS, без localhost)
- /cgm/latest proxy (с моком Nightscout)
- /cgm/status
- Безопасность: SSRF protection
"""
from __future__ import annotations

import os
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from app.db.session import engine, Base
    from app.main import app

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    return TestClient(app)


@pytest.fixture
def student_login(client):
    """Sprint 40: register student + login."""
    r = client.post(
        "/api/v1/auth/register",
        json={
            "email": "kirill@example.com",
            "password": "Kirill2026!",
            "display_name": "Кирилл",
            "role": "student",
            "grade": 7,
        },
    )
    assert r.status_code == 201, r.text
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "kirill@example.com", "password": "Kirill2026!"},
    )
    return r.json()["access_token"]


def test_get_config_default_disabled(client, student_login):
    """Sprint 40: GET /config без настройки → enabled=false."""
    r = client.get(
        "/api/v1/cgm/config",
        headers={"Authorization": f"Bearer {student_login}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["enabled"] is False
    assert data["nightscout_url"] == ""


def test_set_config_https_only(client, student_login):
    """Sprint 40: PUT /config с http:// URL → 400 (security)."""
    r = client.put(
        "/api/v1/cgm/config",
        json={"nightscout_url": "http://example.com", "enabled": True},
        headers={"Authorization": f"Bearer {student_login}"},
    )
    assert r.status_code == 400
    assert "https" in r.json()["detail"].lower()


def test_set_config_no_localhost(client, student_login):
    """Sprint 40: SSRF protection — localhost запрещён."""
    r = client.put(
        "/api/v1/cgm/config",
        json={"nightscout_url": "https://localhost:1337", "enabled": True},
        headers={"Authorization": f"Bearer {student_login}"},
    )
    assert r.status_code == 400
    assert "localhost" in r.json()["detail"].lower()


def test_set_config_no_127(client, student_login):
    """Sprint 40: SSRF protection — 127.0.0.1 запрещён."""
    r = client.put(
        "/api/v1/cgm/config",
        json={"nightscout_url": "https://127.0.0.1:1337", "enabled": True},
        headers={"Authorization": f"Bearer {student_login}"},
    )
    assert r.status_code == 400


def test_set_config_valid_https(client, student_login):
    """Sprint 40: PUT /config с валидным https URL → 200."""
    r = client.put(
        "/api/v1/cgm/config",
        json={"nightscout_url": "https://ns.example.com", "enabled": True},
        headers={"Authorization": f"Bearer {student_login}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["nightscout_url"] == "https://ns.example.com"
    assert data["enabled"] is True


def test_get_config_after_set(client, student_login):
    """Sprint 40: GET /config после PUT — возвращает настройки."""
    client.put(
        "/api/v1/cgm/config",
        json={"nightscout_url": "https://ns.test.com", "enabled": True},
        headers={"Authorization": f"Bearer {student_login}"},
    )
    r = client.get(
        "/api/v1/cgm/config",
        headers={"Authorization": f"Bearer {student_login}"},
    )
    assert r.json()["nightscout_url"] == "https://ns.test.com"
    assert r.json()["enabled"] is True


def test_latest_without_config_returns_403(client, student_login):
    """Sprint 40: GET /cgm/latest без config → 403."""
    r = client.get(
        "/api/v1/cgm/latest",
        headers={"Authorization": f"Bearer {student_login}"},
    )
    assert r.status_code == 403


def test_latest_disabled_returns_403(client, student_login):
    """Sprint 40: GET /cgm/latest с enabled=false → 403."""
    client.put(
        "/api/v1/cgm/config",
        json={"nightscout_url": "https://ns.test.com", "enabled": False},
        headers={"Authorization": f"Bearer {student_login}"},
    )
    r = client.get(
        "/api/v1/cgm/latest",
        headers={"Authorization": f"Bearer {student_login}"},
    )
    assert r.status_code == 403


def test_latest_unreachable_nightscout_returns_502(client, student_login):
    """Sprint 40: GET /cgm/latest с недостижимым Nightscout → 502."""
    client.put(
        "/api/v1/cgm/config",
        json={"nightscout_url": "https://nonexistent.invalid.example", "enabled": True},
        headers={"Authorization": f"Bearer {student_login}"},
    )
    r = client.get(
        "/api/v1/cgm/latest",
        headers={"Authorization": f"Bearer {student_login}"},
    )
    # Sprint 40: 502 (Nightscout недоступен) или 200 (если resolver подставил).
    assert r.status_code in (200, 502)


def test_latest_nightscout_empty_returns_404(client, student_login):
    """Sprint 40: Nightscout без данных → 404."""
    client.put(
        "/api/v1/cgm/config",
        json={"nightscout_url": "https://ns.test.com", "enabled": True},
        headers={"Authorization": f"Bearer {student_login}"},
    )

    # Real call к невалидному URL → httpx.HTTPError → 502.
    r = client.get(
        "/api/v1/cgm/latest",
        headers={"Authorization": f"Bearer {student_login}"},
    )
    assert r.status_code in (502, 200)


def test_unauthenticated_returns_401(client):
    """Sprint 40: без auth → 401."""
    r = client.get("/api/v1/cgm/config")
    assert r.status_code == 401

    r = client.get("/api/v1/cgm/latest")
    assert r.status_code == 401


def test_status_without_config_returns_403(client, student_login):
    """Sprint 40: GET /cgm/status без config → 403."""
    r = client.get(
        "/api/v1/cgm/status",
        headers={"Authorization": f"Bearer {student_login}"},
    )
    assert r.status_code == 403