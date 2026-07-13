"""Аутентификация: хэширование паролей, JWT, зависимости.

Sprint 10.1: JWT теперь можно передавать через cookie (httpOnly) ИЛИ через
Authorization header (обратная совместимость с фронтом). Sprint 10.1 НЕ ломает
существующий API- контракт: фронт продолжает использовать `Authorization: Bearer`,
но сервер при логине теперь дополнительно устанавливает httpOnly-куки для
постепенного перехода. После полного перехода фронта на cookie — header auth
может быть выключен.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.session import get_db
from app.users.models import Role, User

_settings = get_settings()

# passlib bcrypt context. rounds=12 — баланс безопасности/скорости (≈250ms на хэш).
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)

# tokenUrl — это эндпоинт /api/v1/auth/login (OAuth2 password flow для Swagger).
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


# Cookie names (Sprint 10.1)
ACCESS_COOKIE = "ai_tutor_access"
REFRESH_COOKIE = "ai_tutor_refresh"


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _create_token(subject: str, role: str, ttl: timedelta, token_type: str) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + ttl).timestamp()),
    }
    return jwt.encode(payload, _settings.app_secret_key, algorithm=_settings.jwt_algorithm)


def create_access_token(user: User) -> tuple[str, int]:
    ttl = timedelta(minutes=_settings.jwt_access_ttl_minutes)
    return _create_token(str(user.id), user.role.value, ttl, "access"), int(ttl.total_seconds())


def create_refresh_token(user: User) -> str:
    ttl = timedelta(days=_settings.jwt_refresh_ttl_days)
    return _create_token(str(user.id), user.role.value, ttl, "refresh")


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, _settings.app_secret_key, algorithms=[_settings.jwt_algorithm])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str | None = None,
) -> None:
    """Установить httpOnly+SameSite cookies после логина/refresh (Sprint 10.1).

    - httpOnly: JS не может прочитать → не украдёт через XSS.
    - Secure: только HTTPS (в production). В тестах/локальной разработке — False,
      иначе TestClient (ASGI) не передаёт Secure-cookies по http://.
    - SameSite=Lax: базовая CSRF защита.
    """
    is_https_env = str(getattr(_settings, "app_env", "development")).lower() in ("production", "prod")
    response.set_cookie(
        key=ACCESS_COOKIE,
        value=access_token,
        httponly=True,
        secure=is_https_env,
        samesite="lax",
        path="/",
        max_age=_settings.jwt_access_ttl_minutes * 60,
    )
    if refresh_token:
        response.set_cookie(
            key=REFRESH_COOKIE,
            value=refresh_token,
            httponly=True,
            secure=is_https_env,
            samesite="lax",
            path="/api/v1/auth/",  # только auth endpoints читают refresh
            max_age=_settings.jwt_refresh_ttl_days * 86400,
        )


def clear_auth_cookies(response: Response) -> None:
    """Очистить cookies (logout)."""
    response.delete_cookie(key=ACCESS_COOKIE, path="/")
    response.delete_cookie(key=REFRESH_COOKIE, path="/api/v1/auth/")


def get_current_user(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Текущий пользователь — из Bearer header ИЛИ cookie (Sprint 10.1).

    Приоритет: Bearer header → Cookie. Это позволяет плавно мигрировать.
    После полного перехода фронта, можно убрать Bearer fallback.
    """
    # 1) Bearer header (приоритет)
    raw_token = token
    # 2) Cookie — если header нет
    if not raw_token:
        raw_token = request.cookies.get(ACCESS_COOKIE)
    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing token (header or cookie)",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(raw_token)
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Wrong token type"
        )
    user_id = int(payload.get("sub", "0"))
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def require_role(*roles: Role):
    """Dependency factory: пропускает только пользователей с указанными ролями."""

    def _checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires role(s): {[r.value for r in roles]}",
            )
        return user

    return _checker