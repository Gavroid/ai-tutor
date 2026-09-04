"""Sprint 3.9.6 — Сервис для AI-провайдеров.

Содержит:
- Шифрование/расшифрование API-ключей (Fernet, ключ из APP_SECRET_KEY).
- Fetch списка моделей с провайдера (GET {base_url}/models).
- Резолвер модели для предмета (subject_id → provider+key+model).
- Test connection (ping провайдера).
"""
from __future__ import annotations

import base64
import hashlib
import logging
import time
from typing import Any, Optional

import httpx
from app.admin.ai_providers import AIModelCatalog, AIProvider, SubjectAIModel
from app.config import get_settings
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


# ----- Encryption -----

def _derive_fernet_key(secret: str) -> bytes:
    """Derive 32-byte Fernet key из APP_SECRET_KEY через SHA256.

    Fernet требует url-safe base64-encoded 32-byte ключ. APP_SECRET_KEY
    произвольной длины — деривируем через SHA256 → 32 bytes → base64.
    """
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def _get_fernet() -> Fernet:
    settings = get_settings()
    return Fernet(_derive_fernet_key(settings.app_secret_key))


def encrypt_api_key(api_key: str) -> bytes:
    return _get_fernet().encrypt(api_key.encode("utf-8"))


def decrypt_api_key(token: bytes) -> str:
    try:
        return _get_fernet().decrypt(bytes(token)).decode("utf-8")
    except InvalidToken:
        # Fallback для случая когда ключ не Fernet (например legacy plain bytes).
        # В Sprint 3.9.6 такого не должно быть, но оставляем защиту.
        try:
            return bytes(token).decode("utf-8")
        except Exception:
            raise ValueError("API-ключ не удаётся расшифровать (APP_SECRET_KEY изменился?)")


def api_key_last4(encrypted: bytes) -> str:
    """Показать только последние 4 символа открытого ключа для UI."""
    try:
        plain = decrypt_api_key(encrypted)
        if len(plain) <= 4:
            return "•" * len(plain)
        return "•" * (len(plain) - 4) + plain[-4:]
    except Exception:
        return "••••"


# ----- Provider CRUD -----

def list_providers(db: Session) -> list[dict[str, Any]]:
    """Список провайдеров с подсчётом моделей."""
    providers = db.execute(select(AIProvider).order_by(AIProvider.id)).scalars().all()
    result = []
    for p in providers:
        d = {
            "id": p.id,
            "name": p.name,
            "kind": p.kind,
            "base_url": p.base_url,
            "api_key_last4": api_key_last4(p.api_key_encrypted),
            "is_active": p.is_active,
            "note": p.note,
            "created_at": p.created_at,
            "updated_at": p.updated_at,
            "models_count": len(p.models),
        }
        result.append(d)
    return result


def get_provider(db: Session, provider_id: int) -> Optional[AIProvider]:
    return db.execute(select(AIProvider).where(AIProvider.id == provider_id)).scalar_one_or_none()


def create_provider(
    db: Session,
    *,
    name: str,
    kind: str,
    base_url: str,
    api_key: str,
    is_active: bool,
    note: Optional[str],
) -> AIProvider:
    # Проверка уникальности имени.
    existing = db.execute(select(AIProvider).where(AIProvider.name == name)).scalar_one_or_none()
    if existing:
        raise ValueError(f"Провайдер с именем «{name}» уже существует (id={existing.id})")

    provider = AIProvider(
        name=name,
        kind=kind,
        base_url=base_url.rstrip("/"),
        api_key_encrypted=encrypt_api_key(api_key),
        is_active=is_active,
        note=note,
    )
    db.add(provider)
    db.commit()
    db.refresh(provider)
    return provider


def update_provider(
    db: Session,
    provider_id: int,
    *,
    name: Optional[str] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    is_active: Optional[bool] = None,
    note: Optional[str] = None,
) -> AIProvider:
    provider = get_provider(db, provider_id)
    if provider is None:
        raise ValueError(f"Провайдер id={provider_id} не найден")

    if name is not None and name != provider.name:
        existing = db.execute(select(AIProvider).where(AIProvider.name == name)).scalar_one_or_none()
        if existing and existing.id != provider_id:
            raise ValueError(f"Провайдер с именем «{name}» уже существует")
        provider.name = name

    if base_url is not None:
        provider.base_url = base_url.rstrip("/")
    if api_key is not None:
        provider.api_key_encrypted = encrypt_api_key(api_key)
    if is_active is not None:
        provider.is_active = is_active
    if note is not None:
        provider.note = note

    db.commit()
    db.refresh(provider)
    return provider


def delete_provider(db: Session, provider_id: int) -> None:
    provider = get_provider(db, provider_id)
    if provider is None:
        raise ValueError(f"Провайдер id={provider_id} не найден")
    db.delete(provider)
    db.commit()


# ----- Model catalog -----

def list_models(db: Session, provider_id: int) -> list[AIModelCatalog]:
    rows = db.execute(
        select(AIModelCatalog)
        .where(AIModelCatalog.provider_id == provider_id)
        .order_by(AIModelCatalog.model_name)
    ).scalars().all()
    return list(rows)


def set_model_active(db: Session, model_id: int, is_active: bool) -> AIModelCatalog:
    m = db.get(AIModelCatalog, model_id)
    if m is None:
        raise ValueError(f"Модель id={model_id} не найдена")
    m.is_active = is_active
    db.commit()
    db.refresh(m)
    return m


def delete_model(db: Session, model_id: int) -> None:
    m = db.get(AIModelCatalog, model_id)
    if m is None:
        raise ValueError(f"Модель id={model_id} не найдена")
    db.delete(m)
    db.commit()


# ----- Fetch models from provider -----

async def fetch_models_from_provider(
    db: Session, provider_id: int, *, timeout: float = 15.0
) -> dict[str, Any]:
    """Дёргает GET {base_url}/models у провайдера и сохраняет новые модели.

    OpenAI-compatible провайдеры (OpenRouter, Groq, OpenAI, MiniMax) отдают
    список в формате: {"data": [{"id": "...", ...}, ...]}.
    Некоторые отдают просто массив. Мы оба варианта умеем.
    """
    provider = get_provider(db, provider_id)
    if provider is None:
        raise ValueError(f"Провайдер id={provider_id} не найден")

    api_key = decrypt_api_key(provider.api_key_encrypted)
    url = f"{provider.base_url}/models"
    headers = {"Authorization": f"Bearer {api_key}"}

    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.get(url, headers=headers)

    if r.status_code >= 400:
        # Возвращаем осмысленную ошибку с телом ответа (без ключа).
        body_snip = r.text[:300] if r.text else ""
        raise RuntimeError(
            f"Провайдер ответил HTTP {r.status_code} на GET /models: {body_snip}"
        )

    data = r.json()
    if isinstance(data, dict) and "data" in data:
        items = data["data"]
    elif isinstance(data, list):
        items = data
    else:
        raise RuntimeError(f"Неожиданный формат ответа от /models: {type(data).__name__}")

    # Парсим имена моделей. Разные провайдеры используют разные поля.
    names: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        # Типичные поля: "id" (OpenAI), "name" (некоторые), "model" (Groq).
        name = item.get("id") or item.get("name") or item.get("model")
        if isinstance(name, str) and name:
            names.append(name)

    if not names:
        raise RuntimeError("Провайдер вернул пустой список моделей")

    # Дедупликация и upsert.
    added = 0
    already = 0
    new_models: list[AIModelCatalog] = []
    for name in names:
        existing = db.execute(
            select(AIModelCatalog).where(
                AIModelCatalog.provider_id == provider_id,
                AIModelCatalog.model_name == name,
            )
        ).scalar_one_or_none()
        if existing is not None:
            already += 1
            continue
        m = AIModelCatalog(
            provider_id=provider_id,
            model_name=name,
            display_name=None,
            is_active=False,  # По умолчанию выключена, админ включит галочкой.
        )
        db.add(m)
        new_models.append(m)
        added += 1

    db.commit()
    for m in new_models:
        db.refresh(m)

    return {
        "provider_id": provider_id,
        "total_fetched": len(names),
        "added": added,
        "already_present": already,
        "models": list_models(db, provider_id),
    }


# ----- Test connection -----

async def test_provider_connection(
    db: Session, provider_id: int, *, timeout: float = 10.0
) -> dict[str, Any]:
    """Ping провайдера. Возвращает статус, latency_ms, error."""
    provider = get_provider(db, provider_id)
    if provider is None:
        raise ValueError(f"Провайдер id={provider_id} не найден")

    api_key = decrypt_api_key(provider.api_key_encrypted)
    url = f"{provider.base_url}/models"
    headers = {"Authorization": f"Bearer {api_key}"}

    started = time.time()
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.get(url, headers=headers)
        latency_ms = int((time.time() - started) * 1000)
    except Exception as exc:
        return {
            "ok": False,
            "status_code": None,
            "error": f"Сетевая ошибка: {type(exc).__name__}: {exc}"[:300],
            "latency_ms": None,
            "models_count": None,
        }

    if r.status_code >= 400:
        body_snip = r.text[:200] if r.text else ""
        return {
            "ok": False,
            "status_code": r.status_code,
            "error": f"HTTP {r.status_code}: {body_snip}",
            "latency_ms": latency_ms,
            "models_count": None,
        }

    # Считаем кол-во моделей в ответе (best-effort).
    models_count = None
    try:
        data = r.json()
        if isinstance(data, dict) and isinstance(data.get("data"), list):
            models_count = len(data["data"])
        elif isinstance(data, list):
            models_count = len(data)
    except Exception:
        pass

    return {
        "ok": True,
        "status_code": r.status_code,
        "error": None,
        "latency_ms": latency_ms,
        "models_count": models_count,
    }


# ----- Subject routing -----

def get_subject_assignment(
    db: Session, subject_id: int
) -> tuple[Optional[AIModelCatalog], Optional[AIModelCatalog]]:
    """Возвращает (primary, fallback) для предмета. Любой может быть None."""
    assignments = (
        db.execute(
            select(SubjectAIModel).where(SubjectAIModel.subject_id == subject_id)
        )
        .scalars()
        .all()
    )
    primary = next((a.model for a in assignments if a.role == "primary"), None)
    fallback = next((a.model for a in assignments if a.role == "fallback"), None)
    return primary, fallback


def assign_model_to_subject(
    db: Session, subject_id: int, *, model_id: int, role: str
) -> SubjectAIModel:
    """Назначить модель на предмет с указанной ролью. Заменяет предыдущее назначение той же роли."""
    # Если назначение с такой ролью уже есть — обновляем model_id.
    existing = db.execute(
        select(SubjectAIModel).where(
            SubjectAIModel.subject_id == subject_id,
            SubjectAIModel.role == role,
        )
    ).scalar_one_or_none()
    if existing is not None:
        existing.model_id = model_id
        db.commit()
        db.refresh(existing)
        return existing

    assignment = SubjectAIModel(subject_id=subject_id, model_id=model_id, role=role)
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


def clear_subject_assignment(db: Session, subject_id: int, *, role: str) -> None:
    """Удалить назначение (например чтобы fallback оставить пустым)."""
    existing = db.execute(
        select(SubjectAIModel).where(
            SubjectAIModel.subject_id == subject_id,
            SubjectAIModel.role == role,
        )
    ).scalar_one_or_none()
    if existing is not None:
        db.delete(existing)
        db.commit()


def resolve_provider_for_subject(
    db: Session, subject_id: int, *, role: str = "primary"
) -> Optional[dict[str, Any]]:
    """Резолвит провайдера для предмета. role='primary' или 'fallback'.

    Возвращает dict или None если для данной роли ничего не настроено.
    """
    primary, fallback = get_subject_assignment(db, subject_id)
    model = primary if role == "primary" else fallback
    if model is None:
        return None
    if not model.is_active:
        return None
    if model.provider is None or not model.provider.is_active:
        return None
    return {
        "provider_id": model.provider.id,
        "provider_name": model.provider.name,
        "base_url": model.provider.base_url,
        "api_key": decrypt_api_key(model.provider.api_key_encrypted),
        "model_name": model.model_name,
    }


def resolve_fallback_for_subject(
    db: Session, subject_id: int
) -> Optional[dict[str, Any]]:
    """То же самое для fallback роли."""
    return resolve_provider_for_subject(db, subject_id, role="fallback")
