"""Sprint 10.1: JWT в httpOnly cookies + refresh rotation."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.auth.security import ACCESS_COOKIE, REFRESH_COOKIE
from app.db.session import Base, SessionLocal, engine
from app.main import app
from app.users import service as user_service
from app.users.schemas import UserCreate


@pytest.fixture()
def registered_user():
    Base.metadata.drop_all(engine)
    engine.dispose()
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        user_service.register_user(
            db,
            UserCreate(
                email="cookie@example.com",
                password="strongpass1",
                display_name="CookieUser",
                role="student",
                grade=7,
            ),
        )
        db.commit()
    finally:
        db.close()


class TestLoginSetsCookies:
    """POST /auth/login устанавливает httpOnly cookies помимо JSON response."""

    def test_login_sets_access_cookie(self, registered_user):
        c = TestClient(app)
        r = c.post(
            "/api/v1/auth/login",
            json={"email": "cookie@example.com", "password": "strongpass1"},
        )
        assert r.status_code == 200
        body = r.json()
        assert "access_token" in body
        assert "refresh_token" in body
        # Cookies должны быть установлены
        assert ACCESS_COOKIE in r.cookies
        assert REFRESH_COOKIE in r.cookies

    def test_login_cookies_are_httponly(self, registered_user):
        """Cookie помечен httpOnly — JS-атака через XSS НЕ сможет украсть токен."""
        c = TestClient(app)
        r = c.post(
            "/api/v1/auth/login",
            json={"email": "cookie@example.com", "password": "strongpass1"},
        )
        # TestClient не показывает httpOnly флаг напрямую, но можно проверить через
        # 'set-cookie' header — он содержит HttpOnly
        set_cookie_headers = r.headers.get_list("set-cookie")
        assert any("HttpOnly" in sc for sc in set_cookie_headers), (
            "No HttpOnly cookies set"
        )
        assert any("SameSite=Lax" in sc or "samesite=lax" in sc.lower() for sc in set_cookie_headers), (
            "SameSite=Lax not set"
        )


class TestAuthViaCookie:
    """Endpoint /me работает через cookie (Sprint 10.1)."""

    def test_me_via_cookie(self, registered_user):
        c = TestClient(app)
        # Логинимся, сохраняем cookies
        r = c.post(
            "/api/v1/auth/login",
            json={"email": "cookie@example.com", "password": "strongpass1"},
        )
        assert r.status_code == 200
        # Используем cookies для GET /me
        r = c.get("/api/v1/auth/me")
        assert r.status_code == 200, f"Cookie auth failed: {r.text}"
        body = r.json()
        assert body["email"] == "cookie@example.com"
        assert body["role"] == "student"

    def test_me_via_header_still_works(self, registered_user):
        """Обратная совместимость: Bearer header всё ещё работает."""
        c = TestClient(app)
        r = c.post(
            "/api/v1/auth/login",
            json={"email": "cookie@example.com", "password": "strongpass1"},
        )
        token = r.json()["access_token"]
        r = c.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200

    def test_me_no_auth_401(self, registered_user):
        """Без token — 401."""
        c = TestClient(app)
        r = c.get("/api/v1/auth/me")
        assert r.status_code in (401, 403)


class TestRefreshRotation:
    """POST /auth/refresh поддерживает cookie И body (rotation)."""

    def test_refresh_via_body(self, registered_user):
        c = TestClient(app)
        r = c.post(
            "/api/v1/auth/login",
            json={"email": "cookie@example.com", "password": "strongpass1"},
        )
        refresh_token = r.json()["refresh_token"]
        # Используем body
        r = c.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert r.status_code == 200
        # Новые токены
        new_tokens = r.json()
        assert new_tokens["access_token"] != refresh_token
        assert "refresh_token" in new_tokens

    def test_refresh_via_cookie(self, registered_user):
        c = TestClient(app)
        r = c.post(
            "/api/v1/auth/login",
            json={"email": "cookie@example.com", "password": "strongpass1"},
        )
        # НЕ передаём body — refresh должен взяться из cookie
        r = c.post("/api/v1/auth/refresh", json={})
        assert r.status_code == 200
        assert "access_token" in r.json()

    def test_refresh_no_token_401(self, registered_user):
        """Без refresh_token вообще — 401."""
        c = TestClient(app)
        # Очищаем cookies перед запросом
        c.cookies.clear()
        r = c.post("/api/v1/auth/refresh", json={})
        assert r.status_code == 401


class TestLogout:
    """POST /auth/logout очищает cookies (Sprint 10.1)."""

    def test_logout_clears_cookies(self, registered_user):
        c = TestClient(app)
        r = c.post(
            "/api/v1/auth/login",
            json={"email": "cookie@example.com", "password": "strongpass1"},
        )
        assert ACCESS_COOKIE in r.cookies
        r = c.post("/api/v1/auth/logout")
        # После logout cookies должны быть пустыми (delete_cookie)
        # TestClient должен отдать Set-Cookie с expires=Thu, 01 Jan 1970...
        cookie_strs = r.headers.get_list("set-cookie")
        # Убеждаемся что есть cookie с expires в прошлом (delete)
        delete_markers = [s for s in cookie_strs if ACCESS_COOKIE in s and ("Max-Age=0" in s or "expires=Thu, 01 Jan 1970" in s)]
        assert len(delete_markers) >= 1, f"No cookie delete detected: {cookie_strs}"
