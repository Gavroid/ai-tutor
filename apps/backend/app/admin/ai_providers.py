"""Sprint 3.9.6 — Мульти-провайдер AI с per-subject маршрутизацией.

Сущности:
- AIProvider: подключение к сервису (OpenRouter, Groq, OpenAI, Anthropic...).
  Хранит base_url, зашифрованный api_key, kind провайдера.
- AIModelCatalog: модели выбранные у провайдера (после /models).
  Не все модели провайдера — только те, что админ включил.
- SubjectAIModel: назначение модели на предмет.
  role = 'primary' (основная) | 'fallback' (запасная).

Безопасность:
- api_key_encrypted: Fernet (symmetric). Ключ берётся из APP_SECRET_KEY
  (тот же что для JWT). Расшифровка только на backend.
- В API ответы НЕ возвращаем ключ — только last4 для UI.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from app.db.session import Base
from app.users.models import BigIntPK
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship


class AIProvider(Base):
    """Подключение к одному AI-сервису (OpenRouter, Groq, OpenAI, ...)."""

    __tablename__ = "ai_providers"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    # Человекочитаемое имя: "OpenRouter основной", "Groq быстрый".
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    # openai_compat | anthropic | google — тип API (для будущего расширения).
    kind: Mapped[str] = mapped_column(String(32), nullable=False, server_default="openai_compat")
    # Базовый URL: https://openrouter.ai/api/v1 или https://api.groq.com/openai/v1.
    base_url: Mapped[str] = mapped_column(String(255), nullable=False)
    # API-ключ, зашифрован Fernet. НЕ отдаётся в API-ответах.
    api_key_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    # True если провайдер активен (можно использовать).
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    # Произвольное примечание (опционально).
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    models: Mapped[list[AIModelCatalog]] = relationship(
        "AIModelCatalog",
        back_populates="provider",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class AIModelCatalog(Base):
    """Модель провайдера, выбранная админом для использования.

    После добавления провайдера админ жмёт «Получить список моделей» →
    backend дёргает {base_url}/models → кладёт всё в эту таблицу.
    Затем админ галочками отмечает какие модели использовать (is_active).
    """

    __tablename__ = "ai_model_catalog"
    __table_args__ = (UniqueConstraint("provider_id", "model_name", name="uq_model_provider_name"),)

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    provider_id: Mapped[int] = mapped_column(
        BigIntPK, ForeignKey("ai_providers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Название модели у провайдера: openai/gpt-5.6-luna, llama-3.3-70b-versatile.
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    # Человекочитаемое имя (опционально, для UI).
    display_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    provider: Mapped[AIProvider] = relationship("AIProvider", back_populates="models")
    subject_assignments: Mapped[list[SubjectAIModel]] = relationship(
        "SubjectAIModel",
        back_populates="model",
        cascade="all, delete-orphan",
    )


class SubjectAIModel(Base):
    """Назначение AI-модели на предмет.

    Для каждого предмета может быть primary (обязательно одна)
    и опциональная fallback (если primary не ответил).
    """

    __tablename__ = "subject_ai_models"
    __table_args__ = (UniqueConstraint("subject_id", "role", name="uq_subject_role"),)

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    subject_id: Mapped[int] = mapped_column(
        BigIntPK, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    model_id: Mapped[int] = mapped_column(
        BigIntPK, ForeignKey("ai_model_catalog.id", ondelete="CASCADE"), nullable=False
    )
    # 'primary' | 'fallback'.
    role: Mapped[str] = mapped_column(String(16), nullable=False, server_default="primary")

    model: Mapped[AIModelCatalog] = relationship("AIModelCatalog", back_populates="subject_assignments")
