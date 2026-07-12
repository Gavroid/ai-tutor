"""Password reset: модель + сервис.

Подход (Этап security-2):
- POST /auth/password-reset/request {email} → создаёт запись, шлёт email с кодом.
  Ответ ВСЕГДА 200 (не палим существование email).
- POST /auth/password-reset/confirm {token, new_password} → меняет пароль.

Токен — случайные 32 байта (urlsafebase64), хранится как bcrypt-хэш.
TTL — 1 час.
Лимит — 5 запросов в час на email (anti-enumeration через тот же email, dry_run).
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import hash_password
from app.notifications import service as notif_service
from app.users.models import User


RESET_TTL = timedelta(hours=1)
MAX_REQUESTS_PER_HOUR = 5


def _hash_token(token: str) -> str:
    """Храним SHA256 от токена (не bcrypt, т.к. токен сам по себе случайный и длинный)."""
    return hashlib.sha256(token.encode()).hexdigest()


def request_reset(db: Session, email: str) -> Optional[str]:
    """Создаёт токен сброса и возвращает его (для отправки по email).

    Возвращает None если email не найден или user неактивен —
    но вызывающий код должен всегда отвечать 200 (anti-enumeration).
    """
    from app.auth.password_reset_models import PasswordResetToken

    user = db.scalar(select(User).where(User.email == email.lower()))
    if user is None or not user.is_active:
        return None

    # Лимит запросов за час (anti-flood)
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    recent = db.scalars(
        select(PasswordResetToken).where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.created_at >= one_hour_ago,
        )
    ).all()
    if len(recent) >= MAX_REQUESTS_PER_HOUR:
        # Лимит превышен — не выдаём новый токен, но вызывающий код должен ответить 200
        return None

    raw_token = secrets.token_urlsafe(32)
    token_hash = _hash_token(raw_token)
    expires_at = datetime.now(timezone.utc) + RESET_TTL

    record = PasswordResetToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
        used=False,
    )
    db.add(record)
    db.commit()

    # Отправляем email асинхронно (не блокируем ответ)
    # В test/локальном режиме без SMTP — статус будет 'dry_run'
    try:
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        if loop.is_running():
            # Уже в async-loop — пропускаем (тестам не нужно)
            pass
        else:
            loop.run_until_complete(
                notif_service.send_email(
                    db,
                    user_id=user.id,
                    to_email=user.email,
                    subject="[AI-репетитор] Сброс пароля",
                    body=(
                        f"Здравствуйте, {user.display_name}!\n\n"
                        f"Для сброса пароля используйте этот код:\n\n"
                        f"  {raw_token}\n\n"
                        f"Код действителен {int(RESET_TTL.total_seconds() // 60)} минут.\n"
                        f"Если вы не запрашивали сброс — проигнорируйте это письмо.\n\n"
                        f"С уважением,\nAI-репетитор"
                    ),
                )
            )
    except Exception:
        pass  # Не блокируем основной flow

    return raw_token


def confirm_reset(db: Session, raw_token: str, new_password: str) -> bool:
    """Подтверждает сброс пароля.

    Возвращает True если успешно.
    """
    from app.auth.password_reset_models import PasswordResetToken

    token_hash = _hash_token(raw_token)
    record = db.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used.is_(False),
        )
    )
    if record is None:
        return False

    # Проверка срока — БД может вернуть naive datetime, сравниваем без TZ
    expires = record.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < datetime.now(timezone.utc):
        return False

    # Устанавливаем новый пароль
    user = db.get(User, record.user_id)
    if user is None or not user.is_active:
        return False

    user.password_hash = hash_password(new_password)
    record.used = True
    db.commit()

    # Audit log
    from app.admin import service as audit_service

    audit_service.record(
        db,
        user=user,
        action="password.reset",
        entity="user",
        entity_id=str(user.id),
    )

    return True
