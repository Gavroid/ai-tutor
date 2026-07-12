"""Сервис регистрации/логина."""
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.security import create_access_token, create_refresh_token, hash_password, verify_password
from app.users import schemas
from app.users.models import Role, StudentProfile, User


def register_user(db: Session, payload: schemas.UserCreate) -> User:
    """Создаёт пользователя + (если student) профиль ученика.

    Raises:
        HTTPException 409 если email уже занят.
    """
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
