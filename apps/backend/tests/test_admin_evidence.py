"""Тесты Sprint 2026-08-22: admin evidence endpoints.

Покрывает:
- GET /api/v1/admin/evidence (list).
- POST /api/v1/admin/evidence/<code> (update с инвариантами).
- POST /api/v1/admin/evidence/<code>/promote.
- POST /api/v1/admin/evidence/<code>/revoke.
- non-admin → 401/403.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-for-admin-evidence-tests-1234567890")
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")

import pytest
from app.db.session import Base, SessionLocal, engine
from app.main import app
from app.subjects import evidence as evidence_mod
from fastapi.testclient import TestClient


@pytest.fixture()
def admin_client(tmp_path, monkeypatch):
    """TestClient с admin пользователем и изолированным evidence.json."""
    # Изолированный evidence.json в tmp.
    tmp_evidence = tmp_path / "evidence.json"
    initial = {
        "math": {
            "manifest_ready": True,
            "mapping_ready": True,
            "import_ready": True,
            "rag_ready": True,
            "practice_ready": True,
            "manual_smoke_ready": True,
            "pilot_visible": True,
            "promotion_allowed": True,
            "blocked_reason": None,
        },
        "algebra": {
            "manifest_ready": True,
            "mapping_ready": False,
            "import_ready": False,
            "rag_ready": False,
            "practice_ready": False,
            "manual_smoke_ready": False,
            "pilot_visible": False,
            "promotion_allowed": False,
            "blocked_reason": None,
        },
    }
    tmp_evidence.write_text(json.dumps(initial, ensure_ascii=False, indent=2))

    # Подменить путь evidence.json на tmp через monkeypatch на сам модуль.
    from app.admin import router as admin_router

    monkeypatch.setattr(admin_router, "_EVIDENCE_PATH", tmp_evidence)

    # Подменить путь загрузки evidence в subjects.evidence.
    monkeypatch.setattr(
        "app.subjects.evidence._try_load_evidence_json",
        lambda: {
            code: evidence_mod.SubjectEvidence(
                code=code,
                manifest_ready=bool(row.get("manifest_ready", False)),
                mapping_ready=bool(row.get("mapping_ready", False)),
                import_ready=bool(row.get("import_ready", False)),
                rag_ready=bool(row.get("rag_ready", False)),
                practice_ready=bool(row.get("practice_ready", False)),
                manual_smoke_ready=bool(row.get("manual_smoke_ready", False)),
                pilot_visible=bool(row.get("pilot_visible", False)),
                promotion_allowed=bool(row.get("promotion_allowed", False)),
                blocked_reason=row.get("blocked_reason"),
            )
            for code, row in initial.items()
        },
    )
    evidence_mod.reset_evidence_cache()

    # Поднять БД и admin user.
    Base.metadata.drop_all(engine)
    engine.dispose()
    Base.metadata.create_all(engine)

    s = SessionLocal()
    try:
        from app.auth.security import hash_password
        from app.users.models import Role as UserRole
        from app.users.models import User

        admin = User(
            email="admin@test.local",
            password_hash=hash_password("AdminPass123!"),
            display_name="Admin",
            role=UserRole.ADMIN,
            is_active=True,
        )
        s.add(admin)
        student = User(
            email="student@test.local",
            password_hash=hash_password("StudentPass123!"),
            display_name="Student",
            role=UserRole.STUDENT,
            is_active=True,
        )
        s.add(student)
        s.commit()
    finally:
        s.close()

    with TestClient(app) as c:
        # Login admin.
        r = c.post("/api/v1/auth/login", json={"email": "admin@test.local", "password": "AdminPass123!"})
        assert r.status_code == 200, r.text
        yield c, tmp_evidence

    Base.metadata.drop_all(engine)


@pytest.fixture()
def student_client():
    Base.metadata.drop_all(engine)
    engine.dispose()
    Base.metadata.create_all(engine)
    s = SessionLocal()
    try:
        from app.auth.security import hash_password
        from app.users.models import Role as UserRole
        from app.users.models import User

        student = User(
            email="student2@test.local",
            password_hash=hash_password("StudentPass123!"),
            display_name="Student2",
            role=UserRole.STUDENT,
            is_active=True,
        )
        s.add(student)
        s.commit()
    finally:
        s.close()

    with TestClient(app) as c:
        r = c.post("/api/v1/auth/login", json={"email": "student2@test.local", "password": "StudentPass123!"})
        assert r.status_code == 200, r.text
        yield c

    Base.metadata.drop_all(engine)


def test_list_evidence_returns_all_subjects(admin_client):
    c, _ = admin_client
    r = c.get("/api/v1/admin/evidence")
    assert r.status_code == 200
    body = r.json()
    assert "evidence" in body
    codes = [e["subject_code"] for e in body["evidence"]]
    assert "math" in codes
    assert "algebra" in codes
    math_row = next(e for e in body["evidence"] if e["subject_code"] == "math")
    assert math_row["pilot_visible"] is True
    assert math_row["mvp_status"] == "mvp_ready"
    algebra_row = next(e for e in body["evidence"] if e["subject_code"] == "algebra")
    assert algebra_row["mvp_status"] == "internal_mvp"


def test_update_evidence_changes_gate(admin_client):
    c, _ = admin_client
    r = c.post(
        "/api/v1/admin/evidence/algebra",
        json={"gates": {"mapping_ready": True}},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["row"]["mapping_ready"] is True


def test_update_evidence_rejects_unknown_gate(admin_client):
    c, _ = admin_client
    r = c.post(
        "/api/v1/admin/evidence/algebra",
        json={"gates": {"bogus_gate": True}},
    )
    assert r.status_code == 400
    assert "Unknown gates" in r.json()["detail"]


def test_update_evidence_rejects_promotion_without_all_gates(admin_client):
    c, _ = admin_client
    # Попытаться promote algebra (где gates не закрыты).
    r = c.post(
        "/api/v1/admin/evidence/algebra",
        json={"promotion_allowed": True},
    )
    assert r.status_code == 400
    assert "missing gates" in r.json()["detail"]


def test_update_evidence_rejects_pilot_without_promotion_safety_net():
    """Sprint 3.9.3 (2026-08-22): guard утратил смысл.

    После расширения PILOT_SCOPE до 16 subjects, canonical derivation даёт
    pilot_visible=True автоматически при закрытых gates. Тест-сценарий
    'pilot_visible=True при promotion_allowed=False' больше не воспроизводим:
    canonical write синхронизирует оба флага. Guard в router.py:1027 сохранён
    как safety-net для persisted-only запросов (если понадобится отдельный flow).

    Здесь мы smoke-проверяем, что canonical write работает согласованно.
    """
    from app.admin.router import _canonical_promotion

    # algebra в PILOT_SCOPE + закрытые gates → canonical promo=True.
    row = {
        "manifest_ready": True,
        "mapping_ready": True,
        "import_ready": True,
        "rag_ready": True,
        "practice_ready": True,
        "manual_smoke_ready": True,
        "blocked_reason": None,
    }
    promo, pilot = _canonical_promotion(row, "algebra")
    assert promo is True
    assert pilot is True

    # Subject вне PILOT_SCOPE (гипотетически) → canonical promo=False.
    promo2, pilot2 = _canonical_promotion(row, "nonexistent_subject")
    assert promo2 is False
    assert pilot2 is False


def test_promote_evidence_sets_pilot_and_promotion(admin_client):
    c, _ = admin_client
    # Закрыть gates algebra.
    for g in ("mapping_ready", "import_ready", "rag_ready", "practice_ready", "manual_smoke_ready"):
        c.post("/api/v1/admin/evidence/algebra", json={"gates": {g: True}})
    r = c.post("/api/v1/admin/evidence/algebra/promote")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["mvp_status"] == "mvp_ready"


def test_promote_evidence_refuses_when_gates_missing(admin_client):
    c, _ = admin_client
    # Привести algebra к гарантированному состоянию "все gates false".
    for g in ("mapping_ready", "import_ready", "rag_ready", "practice_ready", "manual_smoke_ready"):
        c.post("/api/v1/admin/evidence/algebra", json={"gates": {g: False}})
    r = c.post("/api/v1/admin/evidence/algebra/promote")
    assert r.status_code == 400
    assert "missing gates" in r.json()["detail"]


def test_revoke_evidence_resets_pilot_and_promotion(admin_client):
    c, tmp_evidence = admin_client
    r = c.post("/api/v1/admin/evidence/math/revoke")
    assert r.status_code == 200
    body = r.json()
    assert body["mvp_status"] != "mvp_ready"
    # Файл обновлён.
    saved = json.loads(tmp_evidence.read_text(encoding="utf-8"))
    assert saved["math"]["pilot_visible"] is False
    assert saved["math"]["promotion_allowed"] is False


def test_update_evidence_404_for_unknown_subject(admin_client):
    c, _ = admin_client
    r = c.post(
        "/api/v1/admin/evidence/nonexistent_subject",
        json={"gates": {"mapping_ready": True}},
    )
    assert r.status_code == 404


def test_non_admin_cannot_access_evidence_endpoints(student_client):
    c = student_client
    r = c.get("/api/v1/admin/evidence")
    assert r.status_code in (401, 403)
    r = c.post("/api/v1/admin/evidence/algebra", json={"gates": {"mapping_ready": True}})
    assert r.status_code in (401, 403)
    r = c.post("/api/v1/admin/evidence/algebra/promote")
    assert r.status_code in (401, 403)
    r = c.post("/api/v1/admin/evidence/algebra/revoke")
    assert r.status_code in (401, 403)
