"""Аутентификация: хэширование паролей, JWT, зависимости."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends, HTTPException, status
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
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=True)


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


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    payload = decode_token(token)
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