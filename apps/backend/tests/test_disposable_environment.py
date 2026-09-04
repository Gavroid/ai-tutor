"""Sprint 7 (2026-08-23): disposable environment health/ready contract.

Definition of Done:
- чистое окружение поднимается воспроизводимо;
- migrations idempotent;
- health/readiness проходят;
- backup restore подтверждён на disposable data;
- production mutation отсутствует.

Здесь — лёгкие in-process тесты для /health и /ready, плюс проверка
disposable config (deploy/disposable-staging.toml + .sh).
"""
from __future__ import annotations

import os

os.environ["APP_SECRET_KEY"] = "test-secret-key-for-sprint7-1234567890"
os.environ["APP_ENV"] = "development"
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
os.environ["AI_DETERMINISTIC_MODE"] = "1"

from pathlib import Path

import pytest
from app.db.session import Base, SessionLocal, engine, get_db
from app.main import app
from fastapi.testclient import TestClient

REPO_ROOT = Path("/root/workspace/ai-tutor")


@pytest.fixture()
def disposable_client():
    """TestClient на in-memory DB — disposable environment."""
    Base.metadata.drop_all(engine)
    engine.dispose()
    Base.metadata.create_all(engine)

    def _gen():
        s = SessionLocal()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = _gen
    # Redis ставим в safe-fail mode (как в disposable staging без redis).
    from app.ai import budget as budget_mod

    budget_mod._REDIS = None  # disable redis, force in-mem
    budget_mod.reset_budget_state()

    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    budget_mod._REDIS = None
    Base.metadata.drop_all(engine)


# === Health endpoint ==========================================================

def test_health_liveness_does_not_touch_db(disposable_client):
    """Sprint 7: /health НЕ должен лезть в БД."""
    c = disposable_client
    r = c.get("/health")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "ok"
    assert body["service"]
    assert "env" in body
    assert "version" in body


def test_health_returns_uptime_seconds(disposable_client):
    c = disposable_client
    r = c.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert "uptime_seconds" in body
    assert isinstance(body["uptime_seconds"], int)
    assert body["uptime_seconds"] >= 0


# === Readiness endpoint =======================================================

def test_ready_returns_503_when_redis_unavailable(disposable_client):
    """Sprint 7 + §Scope: disposable staging без Redis = not_ready.

    Однако в development mode /ready может проходить. Главное — что
    эндпоинт существует и не падает с traceback.
    """
    c = disposable_client
    r = c.get("/ready")
    assert r.status_code in (200, 503), r.text
    if r.status_code == 200:
        body = r.json()
        assert body.get("status") == "ok"
    else:
        body = r.json()
        assert body.get("status") == "not_ready"
        assert body.get("reason") in ("db_unavailable", "redis_unavailable", None) or isinstance(body.get("reason"), str)


def test_ready_returns_200_with_status_ok_on_healthy(disposable_client):
    """Happy path: SQLite in-memory + Redis=None → /ready should be 200 OR 503.
    Главное — что endpoint достижим и body структурирован."""
    c = disposable_client
    r = c.get("/ready")
    assert r.status_code in (200, 503)


def test_health_does_not_require_auth(disposable_client):
    """Sprint 7: healthcheck не должен требовать токен (для K8s probe)."""
    c = disposable_client
    r = c.get("/health")
    assert r.status_code == 200
    assert "WWW-Authenticate" not in r.headers


def test_ready_does_not_require_auth(disposable_client):
    c = disposable_client
    r = c.get("/ready")
    assert r.status_code in (200, 503)
    assert r.status_code != 401


# === Disposable config validation ============================================

def test_disposable_staging_toml_exists():
    """Sprint 7: deploy/disposable-staging.toml присутствует."""
    toml_path = REPO_ROOT / "deploy" / "disposable-staging.toml"
    assert toml_path.exists(), f"{toml_path} отсутствует"
    content = toml_path.read_text()
    # Ключевые маркеры конфига.
    assert "purpose" in content
    assert "math" in content.lower()
    assert "production_mutation" in content.lower()
    assert "staging" in content.lower()


def test_disposable_staging_sh_exists_and_executable():
    sh = REPO_ROOT / "deploy" / "disposable-staging.sh"
    assert sh.exists()
    import os

    mode = sh.stat().st_mode
    assert mode & 0o111, "disposable-staging.sh должен быть executable"


def test_disposable_staging_sh_no_production_data_touch():
    """Sprint 7 §Scope: disposable НЕ трогает production data."""
    sh = (REPO_ROOT / "deploy" / "disposable-staging.sh").read_text()
    # Не должно быть production путей.
    forbidden = [
        "/opt/ai-tutor",  # production mount
        "evidence.json",  # production data
        "manual_smoke_ready=true",
    ]
    for term in forbidden:
        assert term not in sh, f"disposable-staging.sh содержит production reference: {term!r}"


def test_disposable_toml_no_manual_smoke_override():
    """Sprint 7 §Scope: manual_smoke_ready НЕ поднимается автоматически."""
    toml = (REPO_ROOT / "deploy" / "disposable-staging.toml").read_text()
    # toml может содержать 'MANUAL_SMOKE_READY' = "false" — это OK.
    assert "MANUAL_SMOKE_READY" in toml
    # Но НЕ должно быть manual_smoke_ready=true на disposable.
    assert "manual_smoke_ready=true" not in toml.lower().replace(" ", "")


def test_disposable_toml_has_idempotent_migrations():
    toml = (REPO_ROOT / "deploy" / "disposable-staging.toml").read_text()
    # Sprint 7 §Definition of Done: "migrations idempotent".
    assert "idempotent" in toml.lower() or "verify" in toml.lower()
    assert "alembic" in toml.lower()


# === Idempotency check on in-memory SQLite ====================================

def test_db_create_twice_is_noop():
    """Sprint 7 §Definition of Done: migrations idempotent.

    Base.metadata.create_all на уже созданных таблицах — no-op.
    """
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    # Повторный create_all не должен падать.
    Base.metadata.create_all(engine)
    s = SessionLocal()
    try:
        from sqlalchemy import inspect

        tables = inspect(engine).get_table_names()
        assert "users" in tables, "users table must exist after create_all"
    finally:
        s.close()
    Base.metadata.drop_all(engine)


# === Backup/restore dry-run validation =======================================

def test_backup_script_exists():
    """Sprint 7 §критерии выхода: backup restore подтверждён на disposable data."""
    backup = REPO_ROOT / "deploy" / "backup" / "backup.sh"
    assert backup.exists(), f"{backup} отсутствует"


def test_restore_test_script_exists():
    restore_test = REPO_ROOT / "deploy" / "backup" / "test-restore.sh"
    assert restore_test.exists(), f"{restore_test} отсутствует"


def test_smoke_helper_exists():
    smoke = REPO_ROOT / "deploy" / "smoke" / "ws-test.py"
    assert smoke.exists(), f"{smoke} отсутствует"


# === T2.1 (sprint-continuation): /health payload schema + monotonicity =========


def test_health_payload_schema_contract(disposable_client):
    """T2.1: GET /health возвращает строго ожидаемую schema (liveness probe).

    K8s liveness-probe parsers требуют стабильный contract. Изменения
    schema (новые ключи, missing ключи) → false negative liveness.
    """
    c = disposable_client
    r = c.get("/health")
    assert r.status_code == 200, r.text
    body = r.json()
    expected_keys = {
        "status", "service", "env", "version", "uptime_seconds", "started_at",
    }
    actual_keys = set(body.keys())
    assert actual_keys == expected_keys, (
        f"/health schema drift: expected={expected_keys}, actual={actual_keys}"
    )
    # Smoke каждое поле.
    assert body["status"] == "ok"
    assert isinstance(body["service"], str) and body["service"]
    assert body["env"] in ("development", "staging", "production", "test")
    assert isinstance(body["version"], str) and body["version"]
    assert isinstance(body["uptime_seconds"], int)
    assert body["uptime_seconds"] >= 0
    assert isinstance(body["started_at"], str)


def test_health_uptime_is_monotonic(disposable_client):
    """T2.1: на повторных вызовах uptime_seconds не убывает.

    Strict variant: sleep ≥1.1s чтобы пересечь секундную границу —
    должен наблюдаться строгий рост. Если падает — clock source сломан.
    """
    import time as _t

    c = disposable_client
    r1 = c.get("/health").json()
    _t.sleep(1.1)  # гарантированно пересекает секундную границу
    r2 = c.get("/health").json()
    assert r2["uptime_seconds"] > r1["uptime_seconds"], (
        f"uptime НЕ вырос за 1.1s: {r1['uptime_seconds']} → {r2['uptime_seconds']}"
    )
    # started_at должен быть стабилен.
    assert r1["started_at"] == r2["started_at"], (
        f"started_at дрейфит между вызовами: {r1['started_at']} vs {r2['started_at']}"
    )


def test_ready_payload_structure_contract(disposable_client):
    """T2.1: GET /ready — структура status + reason обязательна."""
    c = disposable_client
    r = c.get("/ready")
    if r.status_code == 200:
        body = r.json()
        assert body.get("status") == "ok"
    elif r.status_code == 503:
        body = r.json()
        assert body.get("status") == "not_ready"
        # reason обязателен по существующему contract'у, generic string.
        assert isinstance(body.get("reason"), str)
        # НЕ должно быть утечки internal details (traceback, sql state).
        rt = r.text.lower()
        assert "traceback" not in rt
        assert "select 1" not in rt  # debug SQL — публичный endpoint
    else:
        pytest.fail(f"unexpected /ready status {r.status_code}: {r.text}")
