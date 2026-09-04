"""Sprint 3.23 — Admin endpoint для генерации Telegram bind codes.

POST /api/v1/admin/telegram-code { email } → {code: "abcd1234", expires_at: "..."}

Использует issue_code() из app/bot/telegram_bot.py (та же Postgres).
"""

from __future__ import annotations

from app.bot.telegram_bot import issue_code
from app.common.deps import require_admin
from app.db.session import get_db
from app.users.models import User
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


class IssueTelegramCodeIn(BaseModel):
    email: EmailStr = Field(..., description="Email существующего user'а для привязки Telegram")


class IssueTelegramCodeOut(BaseModel):
    code: str
    email: str
    expires_at: str


@router.post(
    "/telegram-code",
    response_model=IssueTelegramCodeOut,
    summary="Генерирует (или возвращает активный) Telegram bind code для email",
)
def issue_telegram_code(
    payload: IssueTelegramCodeIn,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin()),
):
    """Sprint 3.23: admin выдаёт код для user'а.

    - Передай email существующего активного user'а → issue_code сгенерирует
      8-hex-char code (или вернёт существующий активный).
    - User отправляет этот код в Telegram: /start <email> <code>.
    - Bot валидирует код и пишет binding в telegram_bindings.
    - Код одноразовый, expires через 15 мин.

    Audit: записывается action='telegram.code.issue' в audit_logs.
    """
    from app.admin.service import record as audit_record

    try:
        code = issue_code(email=payload.email)
    except ValueError as e:
        raise HTTPException(400, str(e))

    # Audit log
    try:
        audit_record(
            db,
            user=admin,
            action="telegram.code.issue",
            entity="telegram_bind_codes",
            entity_id=None,
            details={"email": payload.email, "code_prefix": code[:4] + "..."},
            request=None,
        )
        db.commit()
    except Exception:
        db.rollback()  # audit non-critical

    from datetime import UTC, datetime, timedelta

    expires_at = (datetime.now(UTC) + timedelta(minutes=15)).isoformat()
    return IssueTelegramCodeOut(
        code=code,
        email=payload.email.lower(),
        expires_at=expires_at,
    )
