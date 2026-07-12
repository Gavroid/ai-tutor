"""Pydantic-схемы для audit log."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None
    action: str
    entity: str | None
    entity_id: str | None
    details: Any | None
    ip_address: str | None
    created_at: datetime