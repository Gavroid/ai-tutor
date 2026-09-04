"""Sprint 96: server-side i18n tests."""
from __future__ import annotations

import os

os.environ.setdefault("OTEL_SDK_DISABLED", "true")

import pytest

# === get_locale tests ===

def test_get_locale_ru():
    """Sprint 96: 'ru-RU' → 'ru'."""
    from app.i18n import get_locale

    assert get_locale("ru-RU,ru;q=0.9") == "ru"


def test_get_locale_en():
    """Sprint 96: 'en-US' → 'en'."""
    from app.i18n import get_locale

    assert get_locale("en-US,en;q=0.9") == "en"


def test_get_locale_default_fallback():
    """Sprint 96: empty header → default 'ru'."""
    from app.i18n import get_locale

    assert get_locale("") == "ru"
    assert get_locale(None) == "ru"


def test_get_locale_unknown_lang_falls_back():
    """Sprint 96: 'de-DE' → 'ru' (default fallback)."""
    from app.i18n import get_locale

    assert get_locale("de-DE,de;q=0.9") == "ru"


def test_get_locale_priority():
    """Sprint 96: first language in priority list wins."""
    from app.i18n import get_locale

    # 'en' before 'ru' → 'en'
    assert get_locale("en-US,en;q=0.9,ru;q=0.8") == "en"


# === t() translation tests ===

def test_translate_ru():
    """Sprint 96: translation для RU."""
    from app.i18n import t

    assert "Неверный" in t("auth.invalid_credentials", "ru")
    assert "Превышен" in t("ai.budget_exceeded", "ru")


def test_translate_en():
    """Sprint 96: translation для EN."""
    from app.i18n import t

    assert "Invalid email" in t("auth.invalid_credentials", "en")
    assert "Daily AI budget" in t("ai.budget_exceeded", "en")


def test_translate_default_ru():
    """Sprint 96: t() defaults to 'ru'."""
    from app.i18n import t

    # No locale arg → 'ru'
    assert "Неверный" in t("auth.invalid_credentials")


def test_translate_unknown_key_returns_key():
    """Sprint 96: unknown key → return key as fallback."""
    from app.i18n import t

    assert t("nonexistent.key") == "nonexistent.key"


def test_translate_unknown_locale_falls_back():
    """Sprint 96: unknown locale → falls back to 'ru'."""
    from app.i18n import t

    assert "Неверный" in t("auth.invalid_credentials", "fr")  # fr → ru


# === localize_error tests ===

def test_localize_error_basic():
    """Sprint 96: localize_error returns code+message dict."""
    from app.i18n import localize_error

    result = localize_error("auth.invalid_credentials", "ru")
    assert result["code"] == "auth.invalid_credentials"
    assert "Неверный" in result["message"]


def test_localize_error_with_kwargs():
    """Sprint 96: localize_error with format kwargs."""
    from app.i18n import localize_error

    # Add a template message to test formatting
    result = localize_error("validation.password_too_short", "ru", min_length=8)
    assert result["code"] == "validation.password_too_short"
    assert "8" in result["message"] or "минимум" in result["message"]


def test_localize_error_en():
    """Sprint 96: localize_error для EN."""
    from app.i18n import localize_error

    result = localize_error("auth.user_not_found", "en")
    assert "User not found" in result["message"]


# === Module tests ===

def test_i18n_module_imports():
    """Sprint 96: i18n module exports."""
    from app import i18n

    assert hasattr(i18n, "get_locale")
    assert hasattr(i18n, "t")
    assert hasattr(i18n, "localize_error")
    assert hasattr(i18n, "MESSAGES")
    assert "ru" in i18n.MESSAGES
    assert "en" in i18n.MESSAGES


def test_messages_dict_has_both_languages():
    """Sprint 96: MESSAGES dict имеет RU + EN с одинаковыми keys."""
    from app.i18n import MESSAGES

    ru_keys = set(MESSAGES["ru"].keys())
    en_keys = set(MESSAGES["en"].keys())

    # All RU keys должны быть в EN
    assert ru_keys == en_keys, f"Keys mismatch: RU only={ru_keys - en_keys}, EN only={en_keys - ru_keys}"


# === Middleware tests ===

def test_locale_middleware_header_ru():
    """Sprint 96: middleware добавляет X-Locale: ru header."""
    from app.db.session import Base, engine
    from app.main import app
    from fastapi.testclient import TestClient

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    client = TestClient(app)
    r = client.get("/health", headers={"Accept-Language": "ru-RU,ru;q=0.9"})
    assert r.status_code == 200
    assert r.headers.get("X-Locale") == "ru"


def test_locale_middleware_header_en():
    """Sprint 96: middleware добавляет X-Locale: en header."""
    from app.db.session import Base, engine
    from app.main import app
    from fastapi.testclient import TestClient

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    client = TestClient(app)
    r = client.get("/health", headers={"Accept-Language": "en-US,en;q=0.9"})
    assert r.status_code == 200
    assert r.headers.get("X-Locale") == "en"


def test_locale_middleware_default_no_header():
    """Sprint 96: без Accept-Language → default 'ru'."""
    from app.db.session import Base, engine
    from app.main import app
    from fastapi.testclient import TestClient

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    client = TestClient(app)
    r = client.get("/health")
    assert r.headers.get("X-Locale") == "ru"
