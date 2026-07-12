"""Роутер загрузки и поиска учебных материалов.

Sprint 1.1: upload защищён require_teacher_or_admin().
Read-эндпоинты (search, by-topic) — для всех авторизованных.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.admin import service as audit_service
from app.common.deps import User, current_user, require_teacher_or_admin
from app.db.session import get_db
from app.materials import schemas, service
from app.subjects import models as subj_models

router = APIRouter(prefix="/api/v1/materials", tags=["materials"])


@router.post("/upload", response_model=schemas.MaterialOut)
async def upload_material(
    topic_id: int = Form(...),
    source: str | None = Form(None),
    ocr_langs: str | None = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current: User = Depends(require_teacher_or_admin()),
):
    topic = db.get(subj_models.Topic, topic_id)
    if topic is None:
        raise HTTPException(404, "Тема не найдена")

    content = await file.read()
    langs = [x.strip() for x in ocr_langs.split("+")] if ocr_langs else None
    try:
        material = service.save_uploaded_material(
            db, topic, file.filename or "upload.bin", content, source, langs
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    audit_service.record(
        db,
        user=current,
        action="material.upload",
        entity="learning_material",
        entity_id=str(material.id),
        details={"filename": file.filename, "topic_id": topic_id, "size": len(content)},
    )
    return material


@router.get("/search", response_model=list[schemas.MaterialSearchHit])
def search(
    q: str,
    topic_id: int | None = None,
    limit: int = 10,
    db: Session = Depends(get_db),
    current: User = Depends(current_user),
):
    return service.search_materials(db, q, topic_id, min(limit, 50))


@router.get("/topic/{topic_id}", response_model=list[schemas.MaterialOut])
def topic_materials(
    topic_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(current_user),
):
    return db.scalars(
        select(subj_models.LearningMaterial)
        .where(subj_models.LearningMaterial.topic_id == topic_id)
        .order_by(subj_models.LearningMaterial.id)
    ).all()
