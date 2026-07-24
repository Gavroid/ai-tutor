"""Sprint 44: Public invite redemption endpoints (no auth required for validate).

- POST /api/v1/auth/redeem-invite   — validate code (для landing page)
- POST /api/v1/auth/register-with-invite — register + auto-redeem
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.common.deps import get_db

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class RedeemInviteIn(BaseModel):
    code: str = Field(min_length=4, max_length=32)


class RedeemInviteOut(BaseModel):
    valid: bool
    role: str
    note: Optional[str] = None
    expires_at: Optional[datetime] = None
    remaining_uses: int


@router.post("/redeem-invite", response_model=RedeemInviteOut)
def redeem_invite(
    payload: RedeemInviteIn,
    db: Session = Depends(get_db),
) -> RedeemInviteOut:
    """Sprint 44: validate invite code (public, no auth).

    Возвращает role + remaining_uses если valid.
    """
    from app.invites.models import Invite

    invite = db.get(Invite, payload.code)
    if invite is None:
        # Не раскрываем информацию о существовании
        raise HTTPException(status_code=404, detail="Invite code не найден или невалиден")

    # Проверяем expires_at
    if invite.expires_at and invite.expires_at <= datetime.utcnow():
        raise HTTPException(status_code=410, detail="Invite code истёк")

    # Проверяем max_uses
    if invite.uses_count >= invite.max_uses:
        raise HTTPException(status_code=410, detail="Invite code уже использован")

    return RedeemInviteOut(
        valid=True,
        role=invite.role,
        note=invite.note,
        expires_at=invite.expires_at,
        remaining_uses=invite.max_uses - invite.uses_count,
    )