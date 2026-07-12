"""Хранение текущего request в contextvar для audit log.

Middleware сохраняет Request в contextvar при каждом запросе,
а audit_service.record() автоматически берёт его оттуда.

Это позволяет НЕ передавать request в каждый вызов record() —
но при этом корректно фиксировать IP.
"""
from __future__ import annotations

from contextvars import ContextVar
from typing import Optional

from fastapi import Request

# ContextVar хранит текущий Request (или None)
_current_request: ContextVar[Optional[Request]] = ContextVar(
    "_current_request", default=None
)


def get_current_request() -> Optional[Request]:
    """Возвращает текущий Request из contextvar (или None)."""
    return _current_request.get()


def set_current_request(request: Optional[Request]) -> object:
    """Устанавливает Request в contextvar. Возвращает token для reset."""
    return _current_request.set(request)


def reset_current_request(token: object) -> None:
    """Восстанавливает предыдущее значение contextvar."""
    _current_request.reset(token)
