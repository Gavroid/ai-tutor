"""Сервис teacher-модуля: парсеры источников, генерация, workflow.

Sprint 1.2-1.3.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.ai import prompts as ai_prompts
from app.ai import sanitize as ai_sanitize
from app.ai.service import AIService
from app.ai.types import AIMessage, AIRequest, AIProvider
from app.subjects import models as subj_models
from app.teacher import schemas as teacher_schemas
from app.users import models as user_models

logger = logging.getLogger(__name__)


# ============================================================
# Парсеры источников
# ============================================================


@dataclass
class SourceContent:
    text: str
    file_name: str | None = None
    detected_format: str = "text"


def parse_text_source(text: str) -> SourceContent:
    """Источник = чистый текст от Учителя."""
    if not text or not text.strip():
        raise ValueError("Текст источника пустой")
    return SourceContent(text=text.strip())


def parse_topic_source(topic: subj_models.Topic) -> SourceContent:
    """Источник = только topic (без материала). Используем название + описание."""
    parts = [topic.name]
    if topic.description:
        parts.append(topic.description)
    text = ". ".join(parts)
    return SourceContent(text=text, detected_format="topic")


def parse_file_source(file_path: str, mime: str | None = None) -> SourceContent:
    """Источник = файл (PDF/DOCX/TXT). Читаем с диска.

    Поддержка форматов:
    - .txt/.md — простой текст
    - .pdf — pdfplumber
    - .docx — python-docx
    - .png/.jpg — заглушка (OCR уже есть в отдельном endpoint /voice/ocr)
    """
    p = Path(file_path)
    if not p.exists():
        raise ValueError(f"Файл не найден: {file_path}")

    suffix = p.suffix.lower()
    if suffix in (".txt", ".md"):
        text = p.read_text(encoding="utf-8", errors="replace")
        return SourceContent(text=text, file_name=p.name, detected_format="txt")

    if suffix == ".pdf":
        try:
            import pdfplumber  # type: ignore

            with pdfplumber.open(p) as pdf:
                pages = [page.extract_text() or "" for page in pdf.pages]
            text = "\n\n".join(pages).strip()
            return SourceContent(text=text, file_name=p.name, detected_format="pdf")
        except ImportError:
            raise ValueError("PDF не поддерживается (pdfplumber не установлен)") from None
        except Exception as exc:
            raise ValueError(f"Ошибка чтения PDF: {exc}") from exc

    if suffix == ".docx":
        try:
            from docx import Document  # type: ignore

            doc = Document(str(p))
            text = "\n".join(para.text for para in doc.paragraphs).strip()
            return SourceContent(text=text, file_name=p.name, detected_format="docx")
        except ImportError:
            raise ValueError("DOCX не поддерживается (python-docx не установлен)") from None
        except Exception as exc:
            raise ValueError(f"Ошибка чтения DOCX: {exc}") from exc

    raise ValueError(f"Формат {suffix} не поддерживается")


# ============================================================
# AI-генерация: единый шаблон
# ============================================================


SYSTEM_PROMPT_FOR_MATERIAL = """Ты — методист, который помогает школьному Учителю подготовить качественный раздел учебника для ученика 7 класса (12-14 лет).

Твоя задача: на основе ИСХОДНОГО МАТЕРИАЛА (или только названия темы) создать ПОЛНЫЙ УЧЕБНЫЙ РАЗДЕЛ по единому шаблону.

ЕДИНЫЙ ШАБЛОН РАЗДЕЛА (JSON):
{
  "title": "Название темы",
  "purpose": "Зачем эта тема нужна, где применяется в жизни",
  "connection_to_prior": "Связь с ранее изученным (если есть)",
  "key_ideas": [
    {"idea": "Главная мысль 1", "terms": ["термин1", "термин2"]},
    ... (3-7 штук)
  ],
  "rule_or_formula": "Главное правило/формула/дата/причинно-следственная связь",
  "simple_example": "Простой разобранный пример",
  "schema_or_table": "Схема или таблица (в markdown)",
  "misconception": "1 типичное заблуждение ученика",
  "common_mistake": "1 частая ошибка",
  "self_check_questions": ["вопрос1", "вопрос2", "вопрос3"],
  "practice_tasks": [
    {
      "difficulty": "easy|medium|hard",
      "question_text": "Условие задачи",
      "reference_solution": "Эталонное решение для авто-проверки",
      "typical_mistakes": ["типичная ошибка 1"],
      "hint": "Подсказка (раскрывает решение по шагам)"
    }
    ... МИНИМУМ 5 задач (easy/medium/hard)
  ],
  "mini_test": [
    {
      "question_text": "Текст вопроса",
      "options": ["вариант A", "вариант B", "вариант C", "вариант D"],
      "correct_index": 0,
      "explanation": "Почему этот вариант правильный"
    }
    ... 5 вопросов
  ],
  "flashcards": [
    {"question": "Вопрос", "answer": "Ответ"}
    ... 6-10 карточек
  ],
  "ai_uncertainty_notes": ["Что я не уверен / требует проверки учителем"]
}

ПРАВИЛА:
- Пиши ТОЛЬКО валидный JSON (без markdown-блока ```).
- Практические задачи — приоритет №1. Их должно быть минимум 5, разной сложности.
- Все формулы — в читаемом текстовом виде (можно markdown).
- ai_uncertainty_notes — обязательно заполни, если что-то неоднозначно.
- Не придумывай несуществующие даты/имена/формулы.
- Учитывай возраст 12-14 лет: ясный язык, без перегруза терминами.
"""


def build_user_prompt(
    subject_name: str,
    topic_name: str,
    source: SourceContent,
    hint: str | None = None,
) -> str:
    parts = [
        f"Предмет: {subject_name}",
        f"Тема: {topic_name}",
        f"Источник ({source.detected_format}):",
        "---",
        source.text[:15000],  # Жёсткий лимит
        "---",
    ]
    if hint:
        parts.append(f"\nДоп. указание от Учителя: {hint}")
    parts.append(
        "\nСгенерируй раздел по единому шаблону. Верни ТОЛЬКО JSON."
    )
    return "\n".join(parts)


async def call_ai_for_material(
    ai_service: AIService,
    subject_name: str,
    topic_name: str,
    source: SourceContent,
    hint: str | None = None,
) -> teacher_schemas.MaterialContent:
    """Запрос к AI → возврат структурированного материала.

    При ошибке парсинга JSON — возвращает базовый шаблон с предупреждением.
    """
    user_prompt = build_user_prompt(subject_name, topic_name, source, hint)

    req = AIRequest(
        messages=[
            AIMessage(role="system", content=SYSTEM_PROMPT_FOR_MATERIAL),
            AIMessage(role="user", content=user_prompt),
        ],
        mode="generate",
        max_tokens=4000,
        temperature=0.3,
    )

    resp = await ai_service.provider.complete(req)

    # Сначала пробуем structured (если провайдер его вернул)
    if resp.structured:
        try:
            return teacher_schemas.MaterialContent(**resp.structured)
        except Exception as exc:
            logger.warning("structured parse failed: %s; falling back to text", exc)

    # Иначе парсим content как JSON
    text = resp.content.strip()
    # Удаляем markdown-обёртку ```json ... ``` если есть
    if text.startswith("```"):
        # Берём содержимое между ```json (или ```) и ```
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    try:
        data = json.loads(text)
        return teacher_schemas.MaterialContent(**data)
    except Exception as exc:
        logger.warning("JSON parse failed: %s; building fallback", exc)
        # Fallback: минимальная структура из того, что есть
        return _build_fallback_material(topic_name, resp.content)


def _build_fallback_material(topic_name: str, raw: str) -> teacher_schemas.MaterialContent:
    """Если AI не вернул валидный JSON — собираем базовую структуру."""
    return teacher_schemas.MaterialContent(
        title=topic_name,
        purpose="Требует ручной доработки Учителем.",
        key_ideas=[],
        self_check_questions=[],
        practice_tasks=[],
        mini_test=[],
        flashcards=[],
        ai_uncertainty_notes=[
            "AI не вернул структурированный JSON.",
            f"Сырой ответ (первые 500 символов): {raw[:500]}",
        ],
    )


# ============================================================
# Сохранение и workflow
# ============================================================


def save_generated_draft(
    db: Session,
    topic: subj_models.Topic,
    user: user_models.User,
    content: teacher_schemas.MaterialContent,
    source_type: str,
    source_file_path: str | None = None,
) -> subj_models.LearningMaterial:
    """Сохраняет сгенерированный материал как draft со статусом ai_generated."""
    material = subj_models.LearningMaterial(
        topic_id=topic.id,
        title=content.title,
        content=content.model_dump_json(),
        source=source_file_path,
        file_path=source_file_path,
        status="ai_generated",
        generated_by=user.id,
        approved_by=None,
        published_at=None,
        source_type=source_type,
        ai_confidence=json.dumps(
            content.ai_uncertainty_notes, ensure_ascii=False
        ),
    )
    db.add(material)
    db.commit()
    db.refresh(material)
    return material


def save_manual_draft(
    db: Session,
    topic: subj_models.Topic,
    user: user_models.User,
    title: str,
    content_json: str,
    source_type: str = "text",
) -> subj_models.LearningMaterial:
    """Сохранение draft без AI — для ручного ввода Учителя (пока не используется)."""
    material = subj_models.LearningMaterial(
        topic_id=topic.id,
        title=title,
        content=content_json,
        status="draft",
        generated_by=user.id,
        source_type=source_type,
    )
    db.add(material)
    db.commit()
    db.refresh(material)
    return material


# Допустимые переходы workflow
_ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"ai_generated", "teacher_approved", "published"},
    "ai_generated": {"teacher_approved", "draft"},  # draft = откат к редактированию
    "teacher_approved": {"published", "ai_generated"},  # обратно если нашёл ошибку
    "published": {"teacher_approved"},  # только обратно для правок
}


class WorkflowError(Exception):
    """Ошибка перехода workflow."""

    pass


def can_transition(current: str, target: str) -> bool:
    return target in _ALLOWED_TRANSITIONS.get(current, set())


def approve_material(
    db: Session,
    material: subj_models.LearningMaterial,
    user: user_models.User,
) -> subj_models.LearningMaterial:
    """Переход в teacher_approved."""
    if not can_transition(material.status, "teacher_approved"):
        raise WorkflowError(
            f"Невозможно approve из статуса '{material.status}'"
        )
    material.status = "teacher_approved"
    material.approved_by = user.id
    db.commit()
    db.refresh(material)
    return material


def publish_material(
    db: Session,
    material: subj_models.LearningMaterial,
    user: user_models.User,
) -> subj_models.LearningMaterial:
    """Переход в published (только из teacher_approved)."""
    if not can_transition(material.status, "published"):
        raise WorkflowError(
            f"Невозможно publish из статуса '{material.status}' "
            "(требуется teacher_approved)"
        )
    material.status = "published"
    material.published_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(material)
    return material


def unpublish_material(
    db: Session,
    material: subj_models.LearningMaterial,
    user: user_models.User,
) -> subj_models.LearningMaterial:
    """Снять с публикации (published → teacher_approved)."""
    if not can_transition(material.status, "teacher_approved"):
        raise WorkflowError(
            f"Невозможно unpublish из статуса '{material.status}'"
        )
    material.status = "teacher_approved"
    material.published_at = None
    db.commit()
    db.refresh(material)
    return material


def update_material_content(
    db: Session,
    material: subj_models.LearningMaterial,
    new_title: str | None = None,
    new_content: teacher_schemas.MaterialContent | None = None,
) -> subj_models.LearningMaterial:
    """Редактирование Учителем. Если материал был approved/published — откатываем в ai_generated."""
    if new_title is not None:
        material.title = new_title
    if new_content is not None:
        material.content = new_content.model_dump_json()
        material.ai_confidence = json.dumps(
            new_content.ai_uncertainty_notes, ensure_ascii=False
        )
    # Любое редактирование → требует повторного approve
    if material.status in ("teacher_approved", "published"):
        material.status = "ai_generated"
        material.approved_by = None
        material.published_at = None
    db.commit()
    db.refresh(material)
    return material


# ============================================================
# Сборка для ответа API
# ============================================================


def material_to_draft_out(
    material: subj_models.LearningMaterial,
) -> teacher_schemas.MaterialDraftOut:
    """Превращает ORM-модель в API-DTO с парсингом content."""
    try:
        content_data = json.loads(material.content)
        content = teacher_schemas.MaterialContent(**content_data)
    except Exception:
        # Если контент не парсится — отдаём минимальную структуру
        content = teacher_schemas.MaterialContent(
            title=material.title,
            purpose="Не удалось разобрать сохранённый контент.",
            ai_uncertainty_notes=["Битый JSON в БД"],
        )
    return teacher_schemas.MaterialDraftOut(
        id=material.id,
        topic_id=material.topic_id,
        title=material.title,
        content=content,
        status=material.status,
        source_type=material.source_type,
        generated_by=material.generated_by,
        approved_by=material.approved_by,
        published_at=material.published_at,
        created_at=material.created_at,
    )


def material_to_list_item(
    material: subj_models.LearningMaterial,
) -> teacher_schemas.MaterialListItem:
    return teacher_schemas.MaterialListItem(
        id=material.id,
        topic_id=material.topic_id,
        title=material.title,
        status=material.status,
        source_type=material.source_type,
        generated_by=material.generated_by,
        approved_by=material.approved_by,
        published_at=material.published_at,
        created_at=material.created_at,
    )


# ============================================================
# Поиск и фильтрация
# ============================================================


def list_materials_for_teacher(
    db: Session,
    user: user_models.User,
    status_filter: str | None = None,
    topic_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[subj_models.LearningMaterial]:
    """Список материалов для учителя.

    Admin видит все; teacher — только свои (по generated_by).
    """
    from sqlalchemy import select

    q = select(subj_models.LearningMaterial).order_by(
        subj_models.LearningMaterial.id.desc()
    )
    if user.role == user_models.Role.TEACHER:
        q = q.where(subj_models.LearningMaterial.generated_by == user.id)
    if status_filter:
        q = q.where(subj_models.LearningMaterial.status == status_filter)
    if topic_id:
        q = q.where(subj_models.LearningMaterial.topic_id == topic_id)
    q = q.limit(min(limit, 200)).offset(max(offset, 0))
    return list(db.scalars(q).all())


def list_published_for_student(
    db: Session,
    topic_id: int | None = None,
    limit: int = 50,
) -> list[subj_models.LearningMaterial]:
    """Только опубликованные материалы — для ученика."""
    from sqlalchemy import select

    q = select(subj_models.LearningMaterial).where(
        subj_models.LearningMaterial.status == "published"
    )
    if topic_id:
        q = q.where(subj_models.LearningMaterial.topic_id == topic_id)
    q = q.order_by(subj_models.LearningMaterial.id.desc()).limit(min(limit, 200))
    return list(db.scalars(q).all())
