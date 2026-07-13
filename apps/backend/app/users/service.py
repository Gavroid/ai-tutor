"""Сервис регистрации/логина."""
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.security import create_access_token, create_refresh_token, hash_password, verify_password
from app.users import schemas
from app.users.models import Role, StudentProfile, User

# Pilot Core Stage 1 — P1.1.3: единый allowlist ролей для публичной регистрации.
# Импортируется из схем, чтобы источник правды был один и тот же.
from app.users.schemas import PUBLIC_REGISTRATION_ALLOWED_ROLES  # noqa: E402,F401


def register_user(
    db: Session,
    payload: schemas.UserCreate,
    *,
    allow_private_bypass: bool = False,
) -> User:
    """Создаёт пользователя + (если student) профиль ученика.

    Args:
        db: SQLAlchemy session.
        payload: данные регистрации.
        allow_private_bypass: True — пропустить allowlist ролей.
            Используется seed_users CLI и pytest fixtures, которые
            создают teacher/admin через сервис. На публичном пути
            (HTTP /api/v1/auth/register) вызов идёт с дефолтным False.

    Raises:
        HTTPException 409 если email уже занят.
        HTTPException 403 если allow_private_bypass=False и role
            вне PUBLIC_REGISTRATION_ALLOWED_ROLES (P1.1.1 / P1.1.2).
    """
    # Pilot Core Stage 1 — P1.1.3: гейт ролей на уровне сервиса,
    # чтобы все callers (router и прямые) шли через одну точку.
    if not allow_private_bypass and payload.role.value not in PUBLIC_REGISTRATION_ALLOWED_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Role '{payload.role.value}' is not available for self-registration. "
                "Privileged roles (teacher/admin) are created only via the "
                "seed_users CLI (PILOT_SEED_TOKEN required)."
            ),
        )

    existing = db.scalar(select(User).where(User.email == payload.email.lower()))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )

    user = User(
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        display_name=payload.display_name.strip(),
        role=payload.role,
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )

    if payload.role == Role.STUDENT:
        profile = StudentProfile(
            user_id=user.id,
            grade=payload.grade or 7,
        )
        db.add(profile)

    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, email: str, password: str) -> User:
    user = db.scalar(select(User).where(User.email == email.lower()))
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )
    if not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )
    return user


def issue_tokens(user: User) -> schemas.TokenPair:
    access, ttl = create_access_token(user)
    refresh = create_refresh_token(user)
    return schemas.TokenPair(access_token=access, refresh_token=refresh, expires_in=ttl)

def get_user_by_email(db: Session, email: str) -> User | None:
    """Получить пользователя по email (для OAuth и других flows)."""
    from sqlalchemy import select

    return db.scalar(select(User).where(User.email == email.lower()))
