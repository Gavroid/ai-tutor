"""Схемы для учебных материалов."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MaterialOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    topic_id: int
    title: str
    source: str | None
    file_path: str | None
    created_at: datetime


class MaterialSearchHit(BaseModel):
    material_id: int
    topic_id: int
    title: str
    snippet: str
    source: str | None