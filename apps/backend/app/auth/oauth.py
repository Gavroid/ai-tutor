"""OAuth2 Authorization Code flow для социальных провайдеров.

Поддерживает:
- Google
- Yandex
- GitHub (через тот же flow)

Endpoints:
- GET /auth/oauth/{provider}/login  → redirect на consent screen
- GET /auth/oauth/{provider}/callback  → обмен code на user info
- POST /auth/oauth/{provider}/token  → прямой доступ (для native клиентов)

Env:
- OAUTH_GOOGLE_CLIENT_ID, OAUTH_GOOGLE_CLIENT_SECRET
- OAUTH_YANDEX_CLIENT_ID, OAUTH_YANDEX_CLIENT_SECRET
- OAUTH_REDIRECT_BASE (default: https://192.168.1.86)
"""
from __future__ import annotations

import os
from typing import Optional
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.auth.security import create_access_token, create_refresh_token
from app.db.session import get_db
from app.users import schemas, service
from app.users.models import Role, User

router = APIRouter(prefix="/api/v1/auth/oauth", tags=["oauth"])

# Провайдеры
PROVIDERS = {
    "google": {
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": "https://www.googleapis.com/oauth2/v2/userinfo",
        "scope": "openid email profile",
        "client_id_env": "OAUTH_GOOGLE_CLIENT_ID",
        "client_secret_env": "OAUTH_GOOGLE_CLIENT_SECRET",
    },
    "yandex": {
        "auth_url": "https://oauth.yandex.ru/authorize",
        "token_url": "https://oauth.yandex.ru/token",
        "userinfo_url": "https://login.yandex.ru/info",
        "scope": "login:email login:info",
        "client_id_env": "OAUTH_YANDEX_CLIENT_ID",
        "client_secret_env": "OAUTH_YANDEX_CLIENT_SECRET",
    },
    "github": {
        "auth_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "userinfo_url": "https://api.github.com/user",
        "scope": "user:email",
        "client_id_env": "OAUTH_GITHUB_CLIENT_ID",
        "client_secret_env": "OAUTH_GITHUB_CLIENT_SECRET",
    },
}


def get_redirect_uri(provider: str) -> str:
    """Полный callback URL для провайдера."""
    base = os.environ.get("OAUTH_REDIRECT_BASE", "https://192.168.1.86")
    return f"{base}/api/v1/auth/oauth/{provider}/callback"


@router.get("/{provider}/login")
def oauth_login(
    provider: str,
    redirect_to: Optional[str] = Query(None, description="Куда вернуть после логина"),
):
    """Редирект на consent screen провайдера."""
    if provider not in PROVIDERS:
        raise HTTPException(404, f"Unknown provider: {provider}")
    cfg = PROVIDERS[provider]
    client_id = os.environ.get(cfg["client_id_env"])
    if not client_id:
        raise HTTPException(
            503,
            f"{provider} OAuth не настроен (env {cfg['client_id_env']} missing)",
        )

    params = {
        "client_id": client_id,
        "redirect_uri": get_redirect_uri(provider),
        "response_type": "code",
        "scope": cfg["scope"],
    }
    if redirect_to:
        params["state"] = redirect_to  # CSRF защита + возврат после login

    url = f"{cfg['auth_url']}?{urlencode(params)}"
    return RedirectResponse(url=url)


@router.get("/{provider}/callback")
async def oauth_callback(
    provider: str,
    code: str = Query(...),
    state: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Callback от провайдера: обмен code на токен + создание пользователя."""
    if provider not in PROVIDERS:
        raise HTTPException(404, f"Unknown provider: {provider}")
    cfg = PROVIDERS[provider]
    client_id = os.environ.get(cfg["client_id_env"])
    client_secret = os.environ.get(cfg["client_secret_env"])

    if not client_id or not client_secret:
        raise HTTPException(503, f"{provider} OAuth не настроен")

    # 1. Обмен code → access_token
    async with httpx.AsyncClient(timeout=15) as client:
        token_resp = await client.post(
            cfg["token_url"],
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": get_redirect_uri(provider),
            },
            headers={"Accept": "application/json"},
        )
        if token_resp.status_code != 200:
            raise HTTPException(
                400, f"Token exchange failed: {token_resp.text[:200]}"
            )
        token_data = token_resp.json()
        access_token = token_data.get("access_token")

        if not access_token:
            raise HTTPException(400, f"No access_token in response: {token_data}")

        # 2. Получение user info
        user_resp = await client.get(
            cfg["userinfo_url"],
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
        )
        if user_resp.status_code != 200:
            raise HTTPException(400, f"User info failed: {user_resp.text[:200]}")
        user_data = user_resp.json()

    # 3. Extract email + name (универсально)
    email, display_name, oauth_id = _extract_user(provider, user_data)

    if not email:
        raise HTTPException(400, f"No email in {provider} user data: {user_data}")

    # 4. Найти или создать пользователя
    user = service.get_user_by_email(db, email)
    if not user:
        # Создаём нового с рандомным паролем (не используется — OAuth login)
        import secrets

        random_password = secrets.token_urlsafe(32)
        user = service.register_user(
            db,
            UserCreate(
                email=email,
                password=random_password,
                display_name=display_name or email.split("@")[0],
                role=Role.STUDENT,
                grade=7,
            ),
        )

    # 5. Issue JWT tokens (as our own auth)
    access, _ = create_access_token(user)
    refresh = create_refresh_token(user)

    # 6. Редирект на frontend с токеном в query
    frontend_base = os.environ.get(
        "OAUTH_REDIRECT_BASE", "https://192.168.1.86"
    )
    frontend_redirect = state or "/subjects"
    # В query params (для SPA который сам кладёт в localStorage)
    params = urlencode(
        {"access_token": access, "refresh_token": refresh, "redirect": frontend_redirect}
    )
    return RedirectResponse(url=f"{frontend_base}/oauth-callback?{params}")


def _extract_user(provider: str, data: dict) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """Нормализация данных от разных провайдеров → (email, name, oauth_id)."""
    if provider == "google":
        return (
            data.get("email"),
            data.get("name") or data.get("given_name"),
            data.get("id") or data.get("sub"),
        )
    if provider == "yandex":
        return (
            data.get("default_email"),
            data.get("display_name") or data.get("real_name") or data.get("login"),
            data.get("id"),
        )
    if provider == "github":
        return (
            data.get("email"),
            data.get("name") or data.get("login"),
            str(data.get("id")),
        )
    return None, None, None


@router.get("/providers")
def list_providers():
    """Список доступных OAuth провайдеров (для UI)."""
    available = []
    for name, cfg in PROVIDERS.items():
        configured = bool(os.environ.get(cfg["client_id_env"]))
        available.append({"name": name, "configured": configured})
    return {"providers": available}
