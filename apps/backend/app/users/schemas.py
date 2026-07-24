"""Pydantic-схемы пользователей (Этап 2)."""
from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.users.models import Role

# Минимальная валидация пароля: 8+ символов. Подробная политика (буквы/цифры/спецсимволы)
# будет ужесточена в Этапе 11, когда подключим rate limit и audit log.
PasswordStr = Annotated[str, Field(min_length=8, max_length=128)]
DisplayNameStr = Annotated[str, Field(min_length=2, max_length=100)]

# Для LOGIN принимаем любой пароль (даже 1 символ), чтобы не палить существование
# email через ошибку 422 ("пароль слишком короткий") и не отвечать на брутфорс
# уникальными ответами. Все пароли проверяются одинаково через bcrypt → 401.
LoginPasswordStr = Annotated[str, Field(min_length=1, max_length=128)]

# Pilot Core Stage 1 — P1.1.3: явный белый список ролей для ПУБЛИЧНОЙ регистрации.
#
# Политика пилота: teacher и admin — привилегированные роли и создаются ТОЛЬКО
# через seed-скрипт (см. app/scripts/seed_users.py и pilot-core-stage-1.md §P1.1.4).
# Сам allowlist НЕ ставится в pydantic-валидаторе UserCreate: схема остаётся
# свободной для seed_users CLI и для pytest fixtures, а гейт реализован
# на уровне публичного HTTP boundary — см.
# `app/users/service.py::PUBLIC_REGISTRATION_ALLOWED_ROLES` и его
# использование в `app/auth/router.py::register`.
PUBLIC_REGISTRATION_ALLOWED_ROLES: frozenset[str] = frozenset({"student", "parent"})


class UserCreate(BaseModel):
    """Регистрация.

    Схема намеренно НЕ валидирует role против public allowlist — это
    responsibility of the HTTP router (см. auth/router.register) и
    service.register_user(allow_private_bypass=True). Схема остаётся
    свободной для seed_users CLI и существующих RBAC-тестов, где
    teacher/admin учётки создаются напрямую.
    """

    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: PasswordStr
    display_name: DisplayNameStr
    role: Role = Role.STUDENT
    # Только для student:
    grade: int | None = Field(default=None, ge=1, le=11)
    # Sprint 44: optional invite code (от admin/teacher).
    invite_code: str | None = Field(default=None, min_length=4, max_length=32)


class UserLogin(BaseModel):
    """Вход — пароль принимает любой длины (1+), чтобы вернуть 401 а не 422."""

    email: EmailStr
    password: LoginPasswordStr


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # секунды до истечения access


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    display_name: str
    role: Role
    is_active: bool
    created_at: datetime


class StudentProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    grade: int
    preferred_language: str
    learning_style: str | None
    daily_minutes: int | None
    goals: str | None


class StudentProfileUpdate(BaseModel):
    grade: int | None = Field(default=None, ge=1, le=11)
    preferred_language: str | None = Field(default=None, max_length=10)
    learning_style: str | None = None
    daily_minutes: int | None = Field(default=None, ge=5, le=600)
    goals: str | None = None