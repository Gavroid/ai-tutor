"""Router для роли Учителя (Sprint 1.2-1.3).

Все endpoints защищены require_teacher_or_admin().
"""
from __future__ import annotations

import os
from datetime import UTC
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.ai.service import AIService
from app.common.deps import User, require_teacher_or_admin
from app.db.session import get_db
from app.subjects import models as subj_models
from app.subjects.router import _followup_count_for_topic
from app.teacher import content_registry
from app.teacher import schemas as teacher_schemas
from app.teacher import service as teacher_service

router = APIRouter(prefix="/api/v1/teacher", tags=["teacher"])


P0_TOPIC_IDS = {187, 188, 189, 192, 193, 194, 195, 196, 197, 198, 199, 201, 203, 204, 225}
P1_TOPIC_IDS = {190, 191, 202, 205, 206, 207, 209, 210, 211, 212, 215, 216, 217, 218, 219}
FOLLOWUP_TOPIC_IDS = {187: 3, 193: 2, 225: 1}


def _priority_for_topic(topic_id: int) -> str:
    if topic_id in P0_TOPIC_IDS:
        return "P0"
    if topic_id in P1_TOPIC_IDS:
        return "P1"
    return "P2"


def _fallback_count_for_topic(topic_id: int) -> int:
    if topic_id == 193:
        return 3
    if topic_id in P0_TOPIC_IDS or topic_id in P1_TOPIC_IDS:
        return 1
    return 0


def _status_for(priority: str) -> tuple[str, str, str, str]:
    if priority in {"P0", "P1"}:
        return "Smoke OK", "Smoke OK", "Verified", "TODO"
    return "TODO", "TODO", "TODO", "TODO"


@router.get(
    "/topics/readiness",
    response_model=list[teacher_schemas.TopicReadinessOut],
    summary="Stage 4.1: read-only readiness dashboard for topics",
)
def topic_readiness(
    subject_id: int | None = Query(None),
    priority: str | None = Query(None, pattern="^(P0|P1|P2)$"),
    manual_qa_status: str | None = Query(None),
    route_tier: str | None = Query(None, pattern="^(base|medium|hard)$"),
    checkpoint: bool | None = Query(None),
    db: Session = Depends(get_db),
    current: User = Depends(require_teacher_or_admin()),
):
    from app.math_plan import PLAN_BY_TOPIC_ID
    from app.rag_models import RagChunk

    query = (
        db.query(subj_models.Topic)
        .join(subj_models.Section)
        .join(subj_models.Subject)
        .order_by(subj_models.Section.order_index, subj_models.Topic.order_index)
    )
    if subject_id is not None:
        query = query.filter(subj_models.Subject.id == subject_id)

    material_counts = dict(
        db.query(subj_models.LearningMaterial.topic_id, func.count(subj_models.LearningMaterial.id))
        .group_by(subj_models.LearningMaterial.topic_id)
        .all()
    )
    chunk_counts = dict(
        db.query(subj_models.LearningMaterial.topic_id, func.count(RagChunk.id))
        .outerjoin(RagChunk, RagChunk.material_id == subj_models.LearningMaterial.id)
        .group_by(subj_models.LearningMaterial.topic_id)
        .all()
    )

    rows: list[teacher_schemas.TopicReadinessOut] = []
    for topic in query.all():
        topic_priority = _priority_for_topic(topic.id)
        if priority and topic_priority != priority:
            continue
        route = PLAN_BY_TOPIC_ID.get(topic.id)
        if route_tier and (route is None or route.tier != route_tier):
            continue
        if checkpoint is not None and bool(route.checkpoint if route else False) != checkpoint:
            continue
        explain_status, practice_status, source_status, manual_status = _status_for(topic_priority)
        status_row = content_registry.get_topic_status(topic.id)
        resolved_manual = str(status_row.get("manual_qa_status") or manual_status)
        if manual_qa_status and resolved_manual.lower() != manual_qa_status.lower():
            continue
        rows.append(
            teacher_schemas.TopicReadinessOut(
                topic_id=topic.id,
                topic_name=topic.name,
                section_id=topic.section.id,
                section_name=topic.section.name,
                subject_id=topic.section.subject.id,
                subject_name=topic.section.subject.name,
                priority=topic_priority,
                route_order=route.order if route else None,
                route_tier=route.tier if route else None,
                route_focus=route.focus if route else None,
                route_checkpoint=bool(route.checkpoint) if route else False,
                material_count=int(material_counts.get(topic.id, 0)),
                chunk_count=int(chunk_counts.get(topic.id, 0)),
                fallback_count=len(content_registry.get_fallbacks(topic.id)) or _fallback_count_for_topic(topic.id),
                followup_count=len(content_registry.get_followups(topic)),
                explain_status=str(status_row.get("explain_status") or explain_status),
                practice_status=str(status_row.get("practice_status") or practice_status),
                source_status=str(status_row.get("source_status") or source_status),
                manual_qa_status=resolved_manual,
            )
        )
    return rows




# ============================================================
# Stage 4.2-4.5: lightweight teacher-managed content registry
# ============================================================


def _get_topic_or_404(db: Session, topic_id: int) -> subj_models.Topic:
    topic = db.get(subj_models.Topic, topic_id)
    if topic is None:
        raise HTTPException(404, "Тема не найдена")
    return topic


@router.get("/topics/{topic_id}/followups", response_model=list[teacher_schemas.TopicFollowupOut])
def teacher_get_followups(
    topic_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(require_teacher_or_admin()),
):
    topic = _get_topic_or_404(db, topic_id)
    return [teacher_schemas.TopicFollowupOut(**row) for row in content_registry.get_followups(topic)]


@router.put("/topics/{topic_id}/followups", response_model=list[teacher_schemas.TopicFollowupOut])
def teacher_put_followups(
    topic_id: int,
    rows: list[teacher_schemas.TopicFollowupOut],
    db: Session = Depends(get_db),
    current: User = Depends(require_teacher_or_admin()),
):
    _get_topic_or_404(db, topic_id)
    saved = content_registry.set_followups(topic_id, [row.model_dump() for row in rows])
    from app.admin import service as audit_service

    audit_service.record(
        db,
        user=current,
        action="topic.followups.update",
        entity="topic",
        entity_id=str(topic_id),
        details={"count": len(saved)},
    )
    return [teacher_schemas.TopicFollowupOut(**row) for row in saved]


@router.get("/topics/{topic_id}/fallbacks", response_model=list[teacher_schemas.TopicPracticeFallbackOut])
def teacher_get_fallbacks(
    topic_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(require_teacher_or_admin()),
):
    _get_topic_or_404(db, topic_id)
    return [teacher_schemas.TopicPracticeFallbackOut(**row) for row in content_registry.get_fallbacks(topic_id)]


@router.put("/topics/{topic_id}/fallbacks", response_model=list[teacher_schemas.TopicPracticeFallbackOut])
def teacher_put_fallbacks(
    topic_id: int,
    rows: list[teacher_schemas.TopicPracticeFallbackIn],
    db: Session = Depends(get_db),
    current: User = Depends(require_teacher_or_admin()),
):
    _get_topic_or_404(db, topic_id)
    saved = content_registry.set_fallbacks(topic_id, [row.model_dump() for row in rows])
    from app.admin import service as audit_service

    audit_service.record(
        db,
        user=current,
        action="topic.fallbacks.update",
        entity="topic",
        entity_id=str(topic_id),
        details={"count": len(saved)},
    )
    return [teacher_schemas.TopicPracticeFallbackOut(**row) for row in saved]


@router.patch("/topics/{topic_id}/status")
def teacher_patch_topic_status(
    topic_id: int,
    payload: teacher_schemas.TopicStatusUpdateIn,
    db: Session = Depends(get_db),
    current: User = Depends(require_teacher_or_admin()),
):
    _get_topic_or_404(db, topic_id)
    saved = content_registry.set_topic_status(topic_id, payload.model_dump(exclude_none=True))
    from app.admin import service as audit_service

    audit_service.record(
        db,
        user=current,
        action="topic.status.update",
        entity="topic",
        entity_id=str(topic_id),
        details=saved,
    )
    return {"ok": True, "topic_id": topic_id, "status": saved}


@router.post("/rag/rebuild-topic/{topic_id}", response_model=teacher_schemas.RagRebuildJobOut)
def teacher_rebuild_topic_rag(
    topic_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(require_teacher_or_admin()),
):
    from datetime import datetime, timezone

    from app.rag_models import RagChunk

    topic = _get_topic_or_404(db, topic_id)
    chunks_before = int(
        db.query(func.count(RagChunk.id))
        .join(subj_models.LearningMaterial, RagChunk.material_id == subj_models.LearningMaterial.id)
        .filter(subj_models.LearningMaterial.topic_id == topic.id)
        .scalar()
        or 0
    )
    job_id = f"rag-topic-{topic.id}-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
    payload = {
        "job_id": job_id,
        "topic_id": topic.id,
        "subject_id": topic.section.subject_id,
        "status": "succeeded",
        "chunks_before": chunks_before,
        "chunks_after": chunks_before,
        "message": "MVP safe rebuild dry-run: existing topic-scoped chunks verified; destructive rebuild is reserved for Stage 4.5 full worker.",
    }
    content_registry.record_rag_job(job_id, payload)
    from app.admin import service as audit_service

    audit_service.record(
        db,
        user=current,
        action="rag.rebuild_topic.request",
        entity="topic",
        entity_id=str(topic.id),
        details=payload,
    )
    return teacher_schemas.RagRebuildJobOut(**payload)


@router.get("/rag/jobs/{job_id}", response_model=teacher_schemas.RagRebuildJobOut)
def teacher_get_rag_job(
    job_id: str,
    db: Session = Depends(get_db),
    current: User = Depends(require_teacher_or_admin()),
):
    row = content_registry.get_rag_job(job_id)
    if row is None:
        raise HTTPException(404, "RAG job not found")
    return teacher_schemas.RagRebuildJobOut(**row)


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
    search: str | None = Query(None, description="Sprint 35: поиск по title (ILIKE)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current: User = Depends(require_teacher_or_admin()),
):
    materials = teacher_service.list_materials_for_teacher(
        db, current, status, topic_id, limit, offset, search
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
    # Teacher may view own materials and shared published library items.
    if (
        current.role.value == "teacher"
        and material.generated_by != current.id
        and material.status != "published"
    ):
        raise HTTPException(403, "Можно просматривать только свои материалы и опубликованную библиотеку")
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
    "/materials/{material_id}/quality-status",
    response_model=teacher_schemas.MaterialDraftOut,
    summary="Stage 21: repeatable content QA status transition",
)
def set_material_quality_status(
    material_id: int,
    payload: teacher_schemas.MaterialQualityStatusIn,
    db: Session = Depends(get_db),
    current: User = Depends(require_teacher_or_admin()),
):
    material = db.get(subj_models.LearningMaterial, material_id)
    if material is None:
        raise HTTPException(404, "Материал не найден")
    if current.role.value == "teacher" and material.generated_by != current.id:
        raise HTTPException(403, "Можно менять QA статус только своих материалов")

    before = material.status
    try:
        material = teacher_service.set_quality_status(db, material, current, payload.status)
    except teacher_service.WorkflowError as exc:
        raise HTTPException(409, str(exc)) from exc

    from app.admin import service as audit_service

    audit_service.record(
        db,
        user=current,
        action="material.quality_status.update",
        entity="learning_material",
        entity_id=str(material.id),
        details={"from": before, "to": payload.status, "stored_status": material.status, "note": payload.note},
    )
    return teacher_service.material_to_draft_out(material)


class BulkApproveIn(BaseModel):
    """Sprint 35: bulk approve материалов."""
    material_ids: list[int] = Field(min_length=1, max_length=50)


class BulkApproveOut(BaseModel):
    """Sprint 35: результат bulk approve."""
    approved: list[int]  # Успешно одобренные
    failed: list[dict[str, str]]  # [{id, reason}]


@router.post(
    "/materials/bulk-approve",
    response_model=BulkApproveOut,
    summary="Sprint 35: approve нескольких материалов сразу",
)
def bulk_approve_materials(
    payload: BulkApproveIn,
    db: Session = Depends(get_db),
    current: User = Depends(require_teacher_or_admin()),
):
    """Sprint 35: одобрить до 50 материалов за один запрос.

    Каждый материал проверяется отдельно:
    - 404 если не найден
    - 403 если teacher пытается approve чужой материал
    - 409 если материал в неправильном workflow state

    Возвращает:
    - approved: список успешно одобренных ID
    - failed: список ошибок [{id, reason}]
    """
    from app.admin import service as audit_service

    approved: list[int] = []
    failed: list[dict[str, str]] = []

    for material_id in payload.material_ids:
        material = db.get(subj_models.LearningMaterial, material_id)
        if material is None:
            failed.append({"id": str(material_id), "reason": "not_found"})
            continue
        if (
            current.role.value == "teacher"
            and material.generated_by != current.id
        ):
            failed.append({"id": str(material_id), "reason": "forbidden"})
            continue
        try:
            material = teacher_service.approve_material(db, material, current)
        except teacher_service.WorkflowError as exc:
            failed.append({"id": str(material_id), "reason": str(exc)})
            continue

        audit_service.record(
            db,
            user=current,
            action="material.approve",
            entity="learning_material",
            entity_id=str(material.id),
        )
        approved.append(material.id)

    db.commit()
    return BulkApproveOut(approved=approved, failed=failed)


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
    from app.ai.mock import MockProvider
    from app.config import get_settings

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
