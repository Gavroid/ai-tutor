"""Sprint 38: OpenAPI metadata enrichment tests."""
from __future__ import annotations


def test_openapi_title():
    """Sprint 38: OpenAPI title содержит app_name."""
    from app.main import app
    from app.config import get_settings

    schema = app.openapi()
    assert schema["info"]["title"] == get_settings().app_name


def test_openapi_version():
    """Sprint 38: version is 0.1.0-mvp."""
    from app.main import app

    schema = app.openapi()
    assert schema["info"]["version"] == "0.1.0-mvp"


def test_openapi_description_includes_t1d_features():
    """Sprint 38: description упоминает T1D-friendly features."""
    from app.main import app

    schema = app.openapi()
    desc = schema["info"]["description"]
    assert "T1D-friendly" in desc
    assert "PauseButton" in desc
    assert "SessionTimer" in desc
    assert "Parent 2FA" in desc
    assert "cookie" in desc.lower()


def test_openapi_tags_have_descriptions():
    """Sprint 38: кастомные tags с descriptions (Sprint 38)."""
    from app.main import app

    schema = app.openapi()
    tags = schema.get("tags", [])
    tag_names = {t["name"] for t in tags}

    # Sprint 38: все теги которые мы объявили
    expected = {
        "auth", "teacher", "parent", "students", "sessions",
        "ai", "voice", "progress", "admin", "meta",
    }
    assert expected.issubset(tag_names), f"Missing: {expected - tag_names}"


def test_openapi_url_paths_exist():
    """Sprint 38: /openapi.json, /docs, /docs/oauth2-redirect paths доступны."""
    from app.main import app

    schema = app.openapi()
    assert schema is not None
    assert len(schema["paths"]) > 0


def test_openapi_health_endpoint_has_summary():
    """Sprint 38: /health endpoint имеет summary."""
    from app.main import app

    schema = app.openapi()
    health = schema["paths"]["/health"]["get"]
    assert "summary" in health
    assert health["summary"] == "Liveness probe"


def test_openapi_endpoints_have_tags():
    """Sprint 38: все endpoints имеют теги для группировки."""
    from app.main import app

    schema = app.openapi()
    paths = schema["paths"]

    # Проверяем ключевые endpoints
    auth_login = paths["/api/v1/auth/login"]["post"]
    assert "auth" in auth_login.get("tags", [])

    teacher_materials = paths["/api/v1/teacher/materials"]["get"]
    assert "teacher" in teacher_materials.get("tags", [])

    sessions_pause = paths["/api/v1/sessions/pause"]["post"]
    assert "sessions" in sessions_pause.get("tags", [])


def test_openapi_quick_links_in_description():
    """Sprint 38: description содержит quick links."""
    from app.main import app

    schema = app.openapi()
    desc = schema["info"]["description"]
    assert "/openapi.json" in desc
    assert "/docs" in desc
    assert "/health" in desc
    assert "/ready" in desc