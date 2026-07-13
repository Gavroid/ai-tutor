"""API v2 каркас (Sprint 10.3).

Назначение: для будущих breaking changes добавлять новые роутеры здесь,
сохраняя v1 нетронутым.

Текущая структура:
  app/v2/__init__.py — этот файл (роутер с примером health-check v2)
  app/v2/{feature}.py — будущие v2-реализации (где потребуется breaking change)

Пока v2 содержит только:
  GET /api/v2/health — показывает что v2 endpoint жив, без полезной нагрузки.

Правила:
- Не импортируйте v1 здесь напрямую — это отдельный namespace.
- Версии несовместимы: v1 будет жить 6+ месяцев после deprecation notice.
- Документация: см. docs/api.md
"""
from __future__ import annotations

from fastapi import APIRouter

from app.common.deps import current_user  # noqa: F401  (готовность для protected endpoints)
from app.users.models import User  # noqa: F401

router = APIRouter(prefix="/api/v2", tags=["v2"])


@router.get("/health")
def v2_health() -> dict:
    """Health-check для v2 namespace (Sprint 10.3).

    Отвечает только если v2 namespace активен. Полезно для мониторинга:
    - POST /api/v2/* — нет, только GET.
    - Возвращает версию для будущего version negotiation.
    """
    return {
        "v2": "ok",
        "api": "ai-tutor",
        "version": "2.0-preview",
        "note": "Sprint 10.3: пока пустой namespace, готов для breaking changes",
    }


@router.get("/info")
def v2_info() -> dict:
    """Информация о v2 API и что нового vs v1.

    Documenting на будущее:
    - v1 остаётся как /api/v1/*
    - v2 не добавляет новых endpoint'ов сейчас; создаётся каркас
    - После того как какой-то из существующих endpoint потребует breaking change,
      будет создан соответствующий /api/v2/{path}
    """
    return {
        "v2_namespace": "active",
        "migrated_from_v1": [],  # список путей, перенесённых из v1
        "new_in_v2": [],
        "deprecated_in_v1": [],
    }
