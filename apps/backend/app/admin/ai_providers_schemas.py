"""Sprint 3.9.6 — Pydantic-схемы для AI-провайдеров и назначений моделей на предметы.

Безопасность:
- api_key_encrypted НИКОГДА не возвращается клиенту.
- В ответах отдаём только api_key_last4 для отображения в UI.
- Запись принимает api_key в открытом виде, шифрует на сервере.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

# ----- AI Provider -----

class AIProviderCreate(BaseModel):
    """Создание нового провайдера. api_key в открытом виде — зашифруем на сервере."""

    name: str = Field(..., min_length=1, max_length=64)
    kind: str = Field(default="openai_compat", pattern=r"^(openai_compat|anthropic|google)$")
    base_url: str = Field(..., min_length=8, max_length=255)
    api_key: str = Field(..., min_length=4, max_length=255)
    is_active: bool = True
    note: Optional[str] = Field(default=None, max_length=255)


class AIProviderUpdate(BaseModel):
    """Обновление провайдера. Все поля опциональны (partial update)."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=64)
    base_url: Optional[str] = Field(default=None, min_length=8, max_length=255)
    api_key: Optional[str] = Field(default=None, min_length=4, max_length=255)
    is_active: Optional[bool] = None
    note: Optional[str] = Field(default=None, max_length=255)


class AIProviderOut(BaseModel):
    """Ответ. api_key_encrypted НЕ включается (только last4)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    kind: str
    base_url: str
    api_key_last4: str
    is_active: bool
    note: Optional[str]
    created_at: datetime
    updated_at: datetime
    models_count: int = 0


# ----- AI Model Catalog -----

class AIModelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    provider_id: int
    model_name: str
    display_name: Optional[str]
    is_active: bool
    fetched_at: datetime


class AIModelToggle(BaseModel):
    is_active: bool


class AIFetchResult(BaseModel):
    """Результат /models endpoint провайдера."""

    provider_id: int
    total_fetched: int
    added: int  # Новых моделей добавлено.
    already_present: int
    models: list[AIModelOut]


# ----- Subject AI Model Assignment -----

class SubjectAIModelAssign(BaseModel):
    """Назначение модели на предмет. role: primary | fallback."""

    model_id: int
    role: str = Field(default="primary", pattern=r"^(primary|fallback)$")


class SubjectAIModelOut(BaseModel):
    """Ответ: какие модели назначены на предмет."""

    subject_id: int
    primary: Optional[AIModelOut] = None
    fallback: Optional[AIModelOut] = None


# ----- Test connection -----

class AITestResult(BaseModel):
    """Результат теста подключения."""

    ok: bool
    status_code: Optional[int] = None
    error: Optional[str] = None
    latency_ms: Optional[int] = None
    models_count: Optional[int] = None
