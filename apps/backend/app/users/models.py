"""SQLAlchemy-модели пользователей (Этап 2).

Используем единый шаблон для всех таблиц:
- id: BIGINT (bigint generated identity) → масштабируется до 2^63
- created_at / updated_at с серверным default и ON UPDATE
- пароли хранятся ТОЛЬКО в виде bcrypt-хэша (cost>=12)
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

# В Postgres используется BIGINT (масштабируется до 2^63), в SQLite —
# INTEGER, иначе автоинкремент не работает (SQLite требует именно INTEGER PK
# для ROWID-based автоинкремента).
BigIntPK = BigInteger().with_variant(Integer, "sqlite")


class Role(str, Enum):
    STUDENT = "student"
    PARENT = "parent"
    TEACHER = "teacher"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Role] = mapped_column(
        SAEnum(Role, name="user_role", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=Role.STUDENT,
        index=True,
    )
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    student_profile: Mapped["StudentProfile | None"] = relationship(
        "StudentProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )


class StudentProfile(Base):
    __tablename__ = "student_profiles"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigIntPK, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    grade: Mapped[int] = mapped_column(Integer, nullable=False, default=7)
    preferred_language: Mapped[str] = mapped_column(String(10), default="ru", nullable=False)
    # learning_style — JSON-строка со свободной структурой (коротко/с примерами/пошагово…)
    learning_style: Mapped[str | None] = mapped_column(Text, nullable=True)
    daily_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    goals: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user: Mapped[User] = relationship("User", back_populates="student_profile")


class ParentStudentLink(Base):
    __tablename__ = "parent_student_links"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    parent_id: Mapped[int] = mapped_column(
        BigIntPK, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    student_id: Mapped[int] = mapped_column(
        BigIntPK, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # "active" / "pending" / "revoked"
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Parent2FA(Base):
    """Sprint 32 P3 — TOTP 2FA для роли parent.

    Хранит:
    - secret_encrypted: Fernet-encrypted TOTP base32 secret.
    - backup_codes_json: JSON list of bcrypt-хэшей (8 одноразовых кодов).
    - enabled_at / last_used_at для аудита.

    Sprint 32 NOTE: при потере пароля → admin reset требует disable 2FA вручную.
    """

    __tablename__ = "parent_2fa"

    parent_id: Mapped[int] = mapped_column(
        BigIntPK, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    secret_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    backup_codes_json: Mapped[str] = mapped_column(Text, nullable=False)
    enabled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )