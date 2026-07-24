"""Sprint 44: Invite management endpoints (admin/teacher).

Endpoints:
- POST   /api/v1/admin/invites           — create invite
- GET    /api/v1/admin/invites           — list invites
- GET    /api/v1/admin/invites/{code}    — get details
- DELETE /api/v1/admin/invites/{code}    — delete unused
- POST   /api/v1/auth/redeem-invite      — validate code (public)
"""
from __future__ import annotations

import secrets
import string
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.deps import User, get_current_user
from app.db.session import get_db
from app.invites.models import Invite

router = APIRouter(prefix="/api/v1/admin/invites", tags=["admin"])


# === Schemas ===

class InviteCreateIn(BaseModel):
    role: str = Field(default="student", description="student | parent | teacher")
    note: str | None = Field(default=None, max_length=255)
    expires_in_days: int | None = Field(default=None, ge=1, le=365)
    max_uses: int = Field(default=1, ge=1, le=100)


class InviteOut(BaseModel):
    code: str
    role: str
    note: str | None
    expires_at: datetime | None
    max_uses: int
    uses_count: int
    created_at: datetime
    is_valid: bool
    is_expired: bool

    class Config:
        from_attributes = True


# === Helper ===

def _generate_code(length: int = 8) -> str:
    """Sprint 44: 8-char code без confusing chars (0/O, 1/I/l)."""
    alphabet = "".join(c for c in (string.ascii_uppercase + string.digits) if c not in "0O1IL")
    return "".join(secrets.choice(alphabet) for _ in range(length))


# === Admin endpoints (require admin/teacher) ===

@router.post("", response_model=InviteOut, status_code=201)
def create_invite(
    payload: InviteCreateIn,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InviteOut:
    """Sprint 44: создать invite code (admin/teacher)."""
    if current.role not in ("admin", "teacher"):
        raise HTTPException(403, "Только admin/teacher могут создавать invites")

    # Sprint 44: generate unique code (max 10 attempts)
    for _ in range(10):
        code = _generate_code()
        existing = db.get(Invite, code)
        if existing is None:
            break
    else:
        raise HTTPException(500, "Не удалось сгенерировать уникальный code")

    expires_at = None
    if payload.expires_in_days:
        from datetime import timedelta
        expires_at = datetime.utcnow() + timedelta(days=payload.expires_in_days)

    invite = Invite(
        code=code,
        created_by=current.id,
        role=payload.role,
        note=payload.note,
        expires_at=expires_at,
        max_uses=payload.max_uses,
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)

    return InviteOut(
        code=invite.code,
        role=invite.role,
        note=invite.note,
        expires_at=invite.expires_at,
        max_uses=invite.max_uses,
        uses_count=invite.uses_count,
        created_at=invite.created_at,
        is_valid=invite.uses_count < invite.max_uses and (
            invite.expires_at is None or invite.expires_at > datetime.utcnow()
        ),
        is_expired=invite.expires_at is not None and invite.expires_at <= datetime.utcnow(),
    )


@router.get("", response_model=list[InviteOut])
def list_invites(
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
) -> list[InviteOut]:
    """Sprint 44: список invites (admin/teacher)."""
    if current.role not in ("admin", "teacher"):
        raise HTTPException(403, "Только admin/teacher")

    rows = db.execute(
        select(Invite)
        .order_by(Invite.created_at.desc())
        .limit(limit)
    ).scalars().all()

    return [
        InviteOut(
            code=i.code,
            role=i.role,
            note=i.note,
            expires_at=i.expires_at,
            max_uses=i.max_uses,
            uses_count=i.uses_count,
            created_at=i.created_at,
            is_valid=i.uses_count < i.max_uses and (
                i.expires_at is None or i.expires_at > datetime.utcnow()
            ),
            is_expired=i.expires_at is not None and i.expires_at <= datetime.utcnow(),
        )
        for i in rows
    ]


@router.get("/{code}", response_model=InviteOut)
def get_invite(
    code: str,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InviteOut:
    """Sprint 44: детали invite (admin/teacher)."""
    if current.role not in ("admin", "teacher"):
        raise HTTPException(403, "Только admin/teacher")

    invite = db.get(Invite, code)
    if invite is None:
        raise HTTPException(404, "Invite not found")

    return InviteOut(
        code=invite.code,
        role=invite.role,
        note=invite.note,
        expires_at=invite.expires_at,
        max_uses=invite.max_uses,
        uses_count=invite.uses_count,
        created_at=invite.created_at,
        is_valid=invite.uses_count < invite.max_uses and (
            invite.expires_at is None or invite.expires_at > datetime.utcnow()
        ),
        is_expired=invite.expires_at is not None and invite.expires_at <= datetime.utcnow(),
    )


@router.delete("/{code}", status_code=204)
def delete_invite(
    code: str,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Sprint 44: удалить unused invite."""
    if current.role not in ("admin", "teacher"):
        raise HTTPException(403, "Только admin/teacher")

    invite = db.get(Invite, code)
    if invite is None:
        raise HTTPException(404, "Invite not found")
    if invite.uses_count > 0:
        raise HTTPException(409, "Нельзя удалить использованный invite")

    db.delete(invite)
    db.commit()
    return None
