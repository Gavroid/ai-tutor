"""S3.6 (2026-09-01, D2.6): Feedback report models.

Модели для таблицы feedback_reports. Создаётся через alembic миграцию 0022.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


# Helper: id column совместимый с SQLite in-memory и PostgreSQL.
# SQLite обрабатывает INTEGER PRIMARY KEY автоматически как ROWID.
# PostgreSQL использует BIGSERIAL для big int.
def _id_column() -> BigInteger:
    """S3.6: BIGINT PK with autoincrement that works on SQLite + Postgres."""
    from sqlalchemy import BigInteger as _B

    return _B().with_variant(Integer, "sqlite")


# Категории feedback report
FB_CATEGORY_ERROR = "error"  # AI вернул неверный ответ
FB_CATEGORY_BUG = "bug"  # Технический баг в UI/backend
FB_CATEGORY_UNCLEAR = "unclear"  # Тема плохо объяснена
FB_CATEGORY_WRONG_ANSWER = "wrong_answer"  # Задание проверки имеет неправильный answer
FB_CATEGORY_OTHER = "other"

FB_CATEGORY_VALUES = (
    FB_CATEGORY_ERROR,
    FB_CATEGORY_BUG,
    FB_CATEGORY_UNCLEAR,
    FB_CATEGORY_WRONG_ANSWER,
    FB_CATEGORY_OTHER,
)

# Статусы
FB_STATUS_OPEN = "open"
FB_STATUS_IN_PROGRESS = "in_progress"
FB_STATUS_RESOLVED = "resolved"
FB_STATUS_WONT_FIX = "wont_fix"

FB_STATUS_VALUES = (
    FB_STATUS_OPEN,
    FB_STATUS_IN_PROGRESS,
    FB_STATUS_RESOLVED,
    FB_STATUS_WONT_FIX,
)


class FeedbackReport(Base):
    __tablename__ = "feedback_reports"

    id = mapped_column(_id_column(), primary_key=True, autoincrement=True)

    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    message_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)  # noqa: F821

    category: Mapped[str] = mapped_column(String(32), nullable=False, default=FB_CATEGORY_OTHER)
    text: Mapped[str] = mapped_column(String(2000), nullable=False)

    status: Mapped[str] = mapped_column(String(16), nullable=False, default=FB_STATUS_OPEN)
    assigned_to: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
