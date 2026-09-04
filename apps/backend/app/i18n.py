"""Sprint 96: server-side i18n для API error messages.

Позволяет возвращать localized error messages в зависимости от
Accept-Language header. По умолчанию — русский (production).
"""

from __future__ import annotations

from typing import Optional

# Sprint 96: messages dict (RU primary, EN fallback).
MESSAGES: dict[str, dict[str, str]] = {
    "ru": {
        "auth.invalid_credentials": "Неверный email или пароль",
        "auth.user_not_found": "Пользователь не найден",
        "auth.account_deactivated": "Аккаунт деактивирован",
        "validation.required": "Обязательное поле",
        "validation.email_invalid": "Некорректный email",
        "validation.password_too_short": "Пароль слишком короткий (минимум 8 символов)",
        "rate_limit.exceeded": "Слишком много запросов, попробуйте позже",
        "server.internal_error": "Внутренняя ошибка сервера",
        "server.not_found": "Не найдено",
        "server.forbidden": "Доступ запрещён",
        "server.unauthorized": "Требуется авторизация",
        "ai.budget_exceeded": "Превышен дневной лимит AI запросов. Попробуйте завтра.",
        "session.paused": "Сессия приостановлена (recovery mode)",
        "rag.not_found": "Документы не найдены",
    },
    "en": {
        "auth.invalid_credentials": "Invalid email or password",
        "auth.user_not_found": "User not found",
        "auth.account_deactivated": "Account is deactivated",
        "validation.required": "Required field",
        "validation.email_invalid": "Invalid email",
        "validation.password_too_short": "Password too short (minimum 8 characters)",
        "rate_limit.exceeded": "Too many requests, try again later",
        "server.internal_error": "Internal server error",
        "server.not_found": "Not found",
        "server.forbidden": "Forbidden",
        "server.unauthorized": "Unauthorized",
        "ai.budget_exceeded": "Daily AI budget exceeded. Try again tomorrow.",
        "session.paused": "Session paused (recovery mode)",
        "rag.not_found": "No documents found",
    },
}


def get_locale(accept_language: Optional[str] = None) -> str:
    """Sprint 96: parse Accept-Language → locale code ('ru' or 'en').

    Примеры:
      "ru-RU,ru;q=0.9,en;q=0.8" → "ru"
      "en-US,en;q=0.9" → "en"
      "de" → "ru" (default fallback)
      "" → "ru"
    """
    if not accept_language:
        return "ru"
    # Parse first 2 letters of first language
    primary = accept_language.split(",")[0].strip().lower()
    if primary.startswith("en"):
        return "en"
    # default → ru
    return "ru"


def t(message_key: str, locale: str = "ru") -> str:
    """Sprint 96: translate message key для given locale.

    Falls back to 'ru' если locale unknown, потом к message_key.
    """
    if locale not in MESSAGES:
        locale = "ru"
    return MESSAGES[locale].get(message_key, MESSAGES["ru"].get(message_key, message_key))


def localize_error(
    message_key: str,
    locale: str = "ru",
    **kwargs: object,
) -> dict[str, str]:
    """Sprint 96: format localized error response.

    Returns:
        {"code": "auth.invalid_credentials", "message": "Неверный email или пароль"}
    """
    msg = t(message_key, locale)
    if kwargs:
        try:
            msg = msg.format(**kwargs)
        except (KeyError, IndexError):
            pass  # leave unformatted
    return {"code": message_key, "message": msg}
