"""Router для роли Учителя (Sprint 1.2-1.3).

Все endpoints защищены require_teacher_or_admin().
"""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.ai.service import AIService
from app.common.deps import User, require_teacher_or_admin
from app.db.session import get_db
from app.subjects import models as subj_models
from app.teacher import schemas as teacher_schemas
from app.teacher import service as teacher_service

router = APIRouter(prefix="/api/v1/teacher", tags=["teacher"])


# ============================================================
# Генерация
# ============================================================


@router.post(
    "/materials/generate",
    response_model=teacher_schemas.MaterialDraftOut,
    summary="AI-генерация черновика материала",
)
async def generate_material(
    payload: teacher_schemas.GenerateMaterialIn,
    db: Session = Depends(get_db),
    current: User = Depends(require_teacher_or_admin()),
):
    """Принимает источник (text/file/topic-only) и возвращает черновик.

    Черновик сохраняется со статусом ai_generated.
    Учитель должен проверить и вызвать /approve → /publish.
    """
    topic = db.get(subj_models.Topic, payload.topic_id)
    if topic is None:
        raise HTTPException(404, "Тема не найдена")

    # === Парсинг источника ===
    if payload.source_type == "text":
        if not payload.text:
            raise HTTPException(400, "Для source_type=text нужно поле text")
        source = teacher_service.parse_text_source(payload.text)
    elif payload.source_type == "file":
        if not payload.file_path:
            raise HTTPException(
                400, "Для source_type=file нужно предварительно загрузить файл"
            )
        source = teacher_service.parse_file_source(payload.file_path)
    elif payload.source_type == "topic":
        source = teacher_service.parse_topic_source(topic)
    else:
        raise HTTPException(400, f"Неизвестный source_type: {payload.source_type}")

    # === Sanitize (защита от инъекций в исходнике) ===
    from app.ai import sanitize as ai_sanitize

    if ai_sanitize.detect_injection(source.text):
        raise HTTPException(
            400,
            "В источнике обнаружены подозрительные конструкции (возможная prompt injection). "
            "Очистите материал и повторите.",
        )

    # === AI-вызов ===
    ai_service = AIService(_get_ai_provider())
    subject_name = topic.section.subject.name if topic.section and topic.section.subject else "Предмет"
    content = await teacher_service.call_ai_for_material(
        ai_service,
        subject_name=subject_name,
        topic_name=topic.name,
        source=source,
        hint=payload.topic_hint,
    )

    # === Сохранение ===
    material = teacher_service.save_generated_draft(
        db,
        topic=topic,
        user=current,
        content=content,
        source_type=payload.source_type,
        source_file_path=payload.file_path,
    )

    # Audit log
    from app.admin import service as audit_service

    audit_service.record(
        db,
        user=current,
        action="material.generate",
        entity="learning_material",
        entity_id=str(material.id),
        details={
            "topic_id": payload.topic_id,
            "source_type": payload.source_type,
            "practice_count": len(content.practice_tasks),
            "uncertainty_count": len(content.ai_uncertainty_notes),
        },
    )

    return teacher_service.material_to_draft_out(material)


@router.post(
    "/materials/upload-source",
    summary="Загрузка файла-источника (PDF/DOCX/TXT)",
)
async def upload_source(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current: User = Depends(require_teacher_or_admin()),
):
    """Загружает файл и возвращает путь — затем его можно использовать в /generate.

    Сохраняем в отдельную подпапку, чтобы не конфликтовать с /materials/upload.
    """
    base_dir = Path(os.environ.get("UPLOAD_DIR", "/var/lib/ai-tutor/uploads"))
    upload_dir = base_dir / "teacher_sources"
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Ограничение размера: 20 МБ
    content = await file.read()
    max_size = 20 * 1024 * 1024
    if len(content) > max_size:
        raise HTTPException(413, f"Файл слишком большой (макс {max_size // (1024*1024)} МБ)")

    # Безопасное имя файла
    safe_name = Path(file.filename or "upload.bin").name
    target = upload_dir / f"src_{current.id}_{safe_name}"
    target.write_bytes(content)

    return {
        "file_path": str(target),
        "size": len(content),
        "filename": safe_name,
    }


# ============================================================
# CRUD
# ============================================================


@router.get(
    "/materials",
    response_model=list[teacher_schemas.MaterialListItem],
    summary="Список материалов (видит свои + admin — все)",
)
def list_materials(
    status: str | None = Query(None),
    topic_id: int | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current: User = Depends(require_teacher_or_admin()),
):
    materials = teacher_service.list_materials_for_teacher(
        db, current, status, topic_id, limit, offset
    )
    return [teacher_service.material_to_list_item(m) for m in materials]


@router.get(
    "/materials/{material_id}",
    response_model=teacher_schemas.MaterialDraftOut,
    summary="Детальный просмотр материала",
)
def get_material(
    material_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(require_teacher_or_admin()),
):
    material = db.get(subj_models.LearningMaterial, material_id)
    if material is None:
        raise HTTPException(404, "Материал не найден")
    # Teacher видит только свои
    if (
        current.role.value == "teacher"
        and material.generated_by != current.id
    ):
        raise HTTPException(403, "Можно просматривать только свои материалы")
    return teacher_service.material_to_draft_out(material)


@router.patch(
    "/materials/{material_id}",
    response_model=teacher_schemas.MaterialDraftOut,
    summary="Редактирование (title/content). Откатывает approved/published в ai_generated.",
)
def update_material(
    material_id: int,
    payload: teacher_schemas.MaterialUpdateIn,
    db: Session = Depends(get_db),
    current: User = Depends(require_teacher_or_admin()),
):
    material = db.get(subj_models.LearningMaterial, material_id)
    if material is None:
        raise HTTPException(404, "Материал не найден")
    if current.role.value == "teacher" and material.generated_by != current.id:
        raise HTTPException(403, "Можно редактировать только свои материалы")

    updated = teacher_service.update_material_content(
        db,
        material,
        new_title=payload.title,
        new_content=payload.content,
    )

    from app.admin import service as audit_service

    audit_service.record(
        db,
        user=current,
        action="material.update",
        entity="learning_material",
        entity_id=str(material.id),
    )

    return teacher_service.material_to_draft_out(updated)


@router.delete(
    "/materials/{material_id}",
    summary="Удаление материала (soft: только draft/ai_generated)",
)
def delete_material(
    material_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(require_teacher_or_admin()),
):
    material = db.get(subj_models.LearningMaterial, material_id)
    if material is None:
        raise HTTPException(404, "Материал не найден")
    if current.role.value == "teacher" and material.generated_by != current.id:
        raise HTTPException(403, "Можно удалять только свои материалы")
    if material.status in ("published", "teacher_approved"):
        raise HTTPException(
            409,
            f"Нельзя удалить материал в статусе '{material.status}'. Сначала снимите с публикации.",
        )

    from app.admin import service as audit_service

    audit_service.record(
        db,
        user=current,
        action="material.delete",
        entity="learning_material",
        entity_id=str(material.id),
        details={"title": material.title, "status_before": material.status},
    )

    db.delete(material)
    db.commit()
    return {"ok": True}


# ============================================================
# Workflow
# ============================================================


@router.post(
    "/materials/{material_id}/approve",
    response_model=teacher_schemas.MaterialDraftOut,
    summary="Перевести в teacher_approved",
)
def approve_material(
    material_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(require_teacher_or_admin()),
):
    material = db.get(subj_models.LearningMaterial, material_id)
    if material is None:
        raise HTTPException(404, "Материал не найден")
    # Approve может сделать teacher (владелец) или admin
    if (
        current.role.value == "teacher"
        and material.generated_by != current.id
    ):
        raise HTTPException(403, "Можно approve только свои материалы")

    try:
        material = teacher_service.approve_material(db, material, current)
    except teacher_service.WorkflowError as exc:
        raise HTTPException(409, str(exc)) from exc

    from app.admin import service as audit_service

    audit_service.record(
        db,
        user=current,
        action="material.approve",
        entity="learning_material",
        entity_id=str(material.id),
    )

    return teacher_service.material_to_draft_out(material)


@router.post(
    "/materials/{material_id}/publish",
    response_model=teacher_schemas.MaterialDraftOut,
    summary="Опубликовать (доступно Ученику)",
)
def publish_material(
    material_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(require_teacher_or_admin()),
):
    material = db.get(subj_models.LearningMaterial, material_id)
    if material is None:
        raise HTTPException(404, "Материал не найден")
    if current.role.value == "teacher" and material.generated_by != current.id:
        raise HTTPException(403, "Можно публиковать только свои материалы")

    try:
        material = teacher_service.publish_material(db, material, current)
    except teacher_service.WorkflowError as exc:
        raise HTTPException(409, str(exc)) from exc

    from app.admin import service as audit_service

    audit_service.record(
        db,
        user=current,
        action="material.publish",
        entity="learning_material",
        entity_id=str(material.id),
    )

    return teacher_service.material_to_draft_out(material)


@router.post(
    "/materials/{material_id}/unpublish",
    response_model=teacher_schemas.MaterialDraftOut,
    summary="Снять с публикации",
)
def unpublish_material(
    material_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(require_teacher_or_admin()),
):
    material = db.get(subj_models.LearningMaterial, material_id)
    if material is None:
        raise HTTPException(404, "Материал не найден")
    if current.role.value == "teacher" and material.generated_by != current.id:
        raise HTTPException(403, "Можно снимать только свои материалы")

    try:
        material = teacher_service.unpublish_material(db, material, current)
    except teacher_service.WorkflowError as exc:
        raise HTTPException(409, str(exc)) from exc

    from app.admin import service as audit_service

    audit_service.record(
        db,
        user=current,
        action="material.unpublish",
        entity="learning_material",
        entity_id=str(material.id),
    )

    return teacher_service.material_to_draft_out(material)


# ============================================================
# Helpers
# ============================================================


def _get_ai_provider():
    """Ленивая инициализация AI-провайдера (как в app.ai)."""
    from app.config import get_settings
    from app.ai.mock import MockProvider

    settings = get_settings()
    api_key = os.environ.get("AI_API_KEY", "").strip()
    if not api_key or api_key == "mock-key-for-tests":
        return MockProvider()
    # Реальный провайдер
    from app.ai.hermes import HermesProvider

    return HermesProvider(
        api_key=api_key,
        base_url=os.environ.get("AI_BASE_URL", "https://api.openai.com/v1"),
        model=os.environ.get("AI_MODEL", "gpt-4o-mini"),
    )
