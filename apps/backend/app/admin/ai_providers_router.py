"""Sprint 3.9.6 — Admin API для AI-провайдеров и назначений моделей на предметы.

Endpoints (все admin-only):
- GET    /api/v1/admin/ai-providers              список провайдеров с models_count
- POST   /api/v1/admin/ai-providers              создать провайдера
- GET    /api/v1/admin/ai-providers/{id}         один провайдер (с моделями)
- PATCH  /api/v1/admin/ai-providers/{id}         обновить
- DELETE /api/v1/admin/ai-providers/{id}         удалить
- POST   /api/v1/admin/ai-providers/{id}/test    ping
- POST   /api/v1/admin/ai-providers/{id}/fetch   получить список моделей
- GET    /api/v1/admin/ai-providers/{id}/models  список моделей
- PATCH  /api/v1/admin/ai-models/{id}            включить/выключить модель (is_active)
- DELETE /api/v1/admin/ai-models/{id}            удалить модель из каталога

- GET    /api/v1/admin/subjects/{id}/ai-assignment    primary + fallback
- PUT    /api/v1/admin/subjects/{id}/ai-assignment    {primary?: model_id, fallback?: model_id}
- DELETE /api/v1/admin/subjects/{id}/ai-assignment/{role}   убрать primary или fallback
"""

from __future__ import annotations

import logging
from typing import Optional

from app.admin import ai_providers as models
from app.admin import ai_providers_schemas as schemas
from app.admin import ai_providers_service as service
from app.common.deps import User, require_admin
from app.db.session import get_db
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/admin/ai-providers",
    tags=["admin", "ai-providers"],
)


# ----- Providers CRUD -----


@router.get("", response_model=list[schemas.AIProviderOut])
def list_providers(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin()),
):
    return service.list_providers(db)


@router.post("", response_model=schemas.AIProviderOut, status_code=201)
async def create_provider(
    payload: schemas.AIProviderCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin()),
):
    try:
        provider = service.create_provider(
            db,
            name=payload.name,
            kind=payload.kind,
            base_url=payload.base_url,
            api_key=payload.api_key,
            is_active=payload.is_active,
            note=payload.note,
        )
    except ValueError as exc:
        raise HTTPException(409, str(exc))

    # Возвращаем в формате list_providers для консистентности.
    return {
        "id": provider.id,
        "name": provider.name,
        "kind": provider.kind,
        "base_url": provider.base_url,
        "api_key_last4": service.api_key_last4(provider.api_key_encrypted),
        "is_active": provider.is_active,
        "note": provider.note,
        "created_at": provider.created_at,
        "updated_at": provider.updated_at,
        "models_count": 0,
    }


@router.get("/{provider_id}", response_model=schemas.AIProviderOut)
def get_provider(
    provider_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin()),
):
    provider = service.get_provider(db, provider_id)
    if provider is None:
        raise HTTPException(404, f"Провайдер id={provider_id} не найден")
    return {
        "id": provider.id,
        "name": provider.name,
        "kind": provider.kind,
        "base_url": provider.base_url,
        "api_key_last4": service.api_key_last4(provider.api_key_encrypted),
        "is_active": provider.is_active,
        "note": provider.note,
        "created_at": provider.created_at,
        "updated_at": provider.updated_at,
        "models_count": len(provider.models),
    }


@router.patch("/{provider_id}", response_model=schemas.AIProviderOut)
def update_provider(
    provider_id: int,
    payload: schemas.AIProviderUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin()),
):
    try:
        provider = service.update_provider(
            db,
            provider_id,
            name=payload.name,
            base_url=payload.base_url,
            api_key=payload.api_key,
            is_active=payload.is_active,
            note=payload.note,
        )
    except ValueError as exc:
        msg = str(exc)
        if "не найден" in msg:
            raise HTTPException(404, msg)
        raise HTTPException(409, msg)

    return {
        "id": provider.id,
        "name": provider.name,
        "kind": provider.kind,
        "base_url": provider.base_url,
        "api_key_last4": service.api_key_last4(provider.api_key_encrypted),
        "is_active": provider.is_active,
        "note": provider.note,
        "created_at": provider.created_at,
        "updated_at": provider.updated_at,
        "models_count": len(provider.models),
    }


@router.delete("/{provider_id}", status_code=204)
def delete_provider(
    provider_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin()),
):
    try:
        service.delete_provider(db, provider_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    return None


@router.post("/{provider_id}/test", response_model=schemas.AITestResult)
async def test_provider(
    provider_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin()),
):
    try:
        result = await service.test_provider_connection(db, provider_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    return result


@router.post("/{provider_id}/fetch", response_model=schemas.AIFetchResult)
async def fetch_models(
    provider_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin()),
):
    try:
        result = await service.fetch_models_from_provider(db, provider_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    except RuntimeError as exc:
        # Провайдер вернул 4xx/5xx или неожиданный формат.
        raise HTTPException(502, f"Провайдер вернул ошибку: {exc}")
    return result


@router.get("/{provider_id}/models", response_model=list[schemas.AIModelOut])
def list_provider_models(
    provider_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin()),
):
    provider = service.get_provider(db, provider_id)
    if provider is None:
        raise HTTPException(404, f"Провайдер id={provider_id} не найден")
    return service.list_models(db, provider_id)


# ----- Models catalog (toggle / delete) -----

# Отдельный router для /ai-models/{id}.
models_router = APIRouter(prefix="/api/v1/admin/ai-models", tags=["admin", "ai-providers"])


@models_router.patch("/{model_id}", response_model=schemas.AIModelOut)
def toggle_model(
    model_id: int,
    payload: schemas.AIModelToggle,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin()),
):
    try:
        m = service.set_model_active(db, model_id, payload.is_active)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    return m


@models_router.delete("/{model_id}", status_code=204)
def delete_model(
    model_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin()),
):
    try:
        service.delete_model(db, model_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    return None


# ----- Subject AI assignment -----

# Роутер для /subjects/{id}/ai-assignment.
subject_ai_router = APIRouter(
    prefix="/api/v1/admin/subjects",
    tags=["admin", "ai-providers", "subjects"],
)


@subject_ai_router.get("/{subject_id}/ai-assignment", response_model=schemas.SubjectAIModelOut)
def get_subject_assignment(
    subject_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin()),
):
    # Проверим что предмет существует.
    from app.subjects.models import Subject

    subj = db.get(Subject, subject_id)
    if subj is None:
        raise HTTPException(404, f"Предмет id={subject_id} не найден")

    primary, fallback = service.get_subject_assignment(db, subject_id)
    return {
        "subject_id": subject_id,
        "primary": primary,
        "fallback": fallback,
    }


class SubjectAIModelPut(BaseModel):
    """PUT для обновления назначений. role → model_id (или None чтобы убрать)."""

    primary: Optional[int] = None
    fallback: Optional[int] = None


@subject_ai_router.put("/{subject_id}/ai-assignment", response_model=schemas.SubjectAIModelOut)
def set_subject_assignment(
    subject_id: int,
    payload: SubjectAIModelPut,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin()),
):
    from app.admin.ai_providers import AIModelCatalog
    from app.subjects.models import Subject

    subj = db.get(Subject, subject_id)
    if subj is None:
        raise HTTPException(404, f"Предмет id={subject_id} не найден")

    # Обрабатываем primary. Семантика:
    # - None (или поле отсутствует) → не трогаем.
    # - 0 → явно очистить.
    # - >0 → назначить.
    if payload.primary is not None:
        if payload.primary == 0:
            service.clear_subject_assignment(db, subject_id, role="primary")
        else:
            m = db.get(AIModelCatalog, payload.primary)
            if m is None:
                raise HTTPException(404, f"Модель id={payload.primary} не найдена")
            service.assign_model_to_subject(db, subject_id, model_id=payload.primary, role="primary")

    if payload.fallback is not None:
        if payload.fallback == 0:
            service.clear_subject_assignment(db, subject_id, role="fallback")
        else:
            m = db.get(AIModelCatalog, payload.fallback)
            if m is None:
                raise HTTPException(404, f"Модель id={payload.fallback} не найдена")
            service.assign_model_to_subject(db, subject_id, model_id=payload.fallback, role="fallback")

    primary, fallback = service.get_subject_assignment(db, subject_id)
    return {
        "subject_id": subject_id,
        "primary": primary,
        "fallback": fallback,
    }
