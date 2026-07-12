"""Модели учебной структуры (Этап 3).

Иерархия: Subject → Section → Topic → Subtopic → LearningMaterial → Question.
Difficulty и recommended_grade — int от 1 (просто) до 5 (сложно).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.users.models import BigIntPK


class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Цвет/иконка для UI (hex + emoji)
    color: Mapped[str | None] = mapped_column(String(20), nullable=True)
    icon: Mapped[str | None] = mapped_column(String(10), nullable=True)
    recommended_grade: Mapped[int] = mapped_column(Integer, default=7, nullable=False)
    age_min: Mapped[int] = mapped_column(Integer, default=12, nullable=False)
    age_max: Mapped[int] = mapped_column(Integer, default=14, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    sections: Mapped[list["Section"]] = relationship(
        "Section", back_populates="subject", cascade="all, delete-orphan", order_by="Section.order_index"
    )


class Section(Base):
    __tablename__ = "sections"
    __table_args__ = (UniqueConstraint("subject_id", "order_index", name="uq_sections_subject_order"),)

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    subject_id: Mapped[int] = mapped_column(
        BigIntPK, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    subject: Mapped[Subject] = relationship("Subject", back_populates="sections")
    topics: Mapped[list["Topic"]] = relationship(
        "Topic", back_populates="section", cascade="all, delete-orphan", order_by="Topic.order_index"
    )


class Topic(Base):
    __tablename__ = "topics"
    __table_args__ = (UniqueConstraint("section_id", "order_index", name="uq_topics_section_order"),)

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    section_id: Mapped[int] = mapped_column(
        BigIntPK, ForeignKey("sections.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    difficulty: Mapped[int] = mapped_column(Integer, default=1, nullable=False)  # 1..5
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    section: Mapped[Section] = relationship("Section", back_populates="topics")
    subtopics: Mapped[list["Subtopic"]] = relationship(
        "Subtopic", back_populates="topic", cascade="all, delete-orphan", order_by="Subtopic.order_index"
    )
    materials: Mapped[list["LearningMaterial"]] = relationship(
        "LearningMaterial", back_populates="topic", cascade="all, delete-orphan"
    )
    questions: Mapped[list["Question"]] = relationship(
        "Question", back_populates="topic", cascade="all, delete-orphan"
    )


class Subtopic(Base):
    __tablename__ = "subtopics"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    topic_id: Mapped[int] = mapped_column(
        BigIntPK, ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    topic: Mapped[Topic] = relationship("Topic", back_populates="subtopics")


class LearningMaterial(Base):
    __tablename__ = "learning_materials"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    topic_id: Mapped[int] = mapped_column(
        BigIntPK, ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str | None] = mapped_column(String(300), nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # === Sprint 1.4: workflow-поля для роли Учителя ===
    # Жизненный цикл: draft → ai_generated → teacher_approved → published.
    # Все существующие записи получат "draft" по умолчанию.
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default="draft", index=True
    )
    generated_by: Mapped[int | None] = mapped_column(
        BigIntPK,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    approved_by: Mapped[int | None] = mapped_column(
        BigIntPK,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    source_type: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="text"
    )
    # JSON-строка (для совместимости с SQLite в тестах): что AI пометил как "не уверен".
    ai_confidence: Mapped[str | None] = mapped_column(Text, nullable=True)

    topic: Mapped[Topic] = relationship("Topic", back_populates="materials")


class Question(Base):
    """Задание. Тип: single, multiple, numeric, text, code, sequence, fill, translation, image, short."""

    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    topic_id: Mapped[int] = mapped_column(
        BigIntPK, ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    difficulty: Mapped[int] = mapped_column(Integer, default=1, nullable=False)  # 1..5
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    # JSON-строка: для single/multiple — варианты, для numeric — допуск,
    # для fill — пропуски, для code — стартовый код и т.д.
    payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    correct_answer: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    # typical_mistakes — JSON-массив строк
    typical_mistakes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    topic: Mapped[Topic] = relationship("Topic", back_populates="questions")