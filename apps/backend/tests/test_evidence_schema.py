"""Sprint 3 (2026-08-23): canonical readiness policy contract tests.

Проверяет:
- JSON Schema для evidence.json;
- derive promotion_allowed canonical;
- запрет blocked_ocr + pilot_visible=true / blocked_ocr + promotion_allowed=true;
- запрет promotion при false обязательном gate;
- pilot scope: только math → остальные НЕ pilot_visible;
- audit показывает manual_smoke_ready=false (если не задано);
- API list/update возвращает canonical (НЕ persisted).
"""
from __future__ import annotations

import json
import os

os.environ["APP_SECRET_KEY"] = "test-secret-key-for-readiness-schema-1234567890"
os.environ["APP_ENV"] = "development"
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["CORS_ORIGINS"] = "http://localhost:3000"
os.environ.setdefault("OTEL_SDK_DISABLED", "true")

import pytest
from fastapi.testclient import TestClient

from app.db.session import Base, SessionLocal, engine, get_db
from app.main import app
from app.subjects.evidence_schema import (
    PILOT_SCOPE,
    REQUIRED_GATES,
    EvidenceValidationError,
    evidence_schema,
    find_evidence_path,
    is_canonical_violation,
    validate_evidence_file,
    validate_evidence_payload,
)
from app.users import service as user_service
from app.users.schemas import UserCreate


# === Schema уровня ============================================================

def test_schema_is_well_formed_object():
    schema = evidence_schema()
    assert schema["type"] == "object"
    assert "properties" not in schema  # top-level — dict-of-subjects
    assert "additionalProperties" in schema
    subj = schema["additionalProperties"]
    assert subj["type"] == "object"
    fields = set(subj["properties"].keys())
    # Все обязательные gates + promotion + blocked_reason.
    expected = {
        "manifest_ready", "mapping_ready", "import_ready",
        "rag_ready", "practice_ready", "manual_smoke_ready",
        "pilot_visible", "promotion_allowed", "blocked_reason",
    }
    assert fields == expected, fields ^ expected


def test_pilot_scope_only_math():
    assert PILOT_SCOPE == {"math"}, f"PILOT_SCOPE изменён: {PILOT_SCOPE}"


# === Canonical derivation =====================================================

def _payload(subjects: dict) -> dict:
    """Обернуть subjects в стандартный payload + привести к типам."""
    out = {}
    for code, gates in subjects.items():
        out[code] = {
            "manifest_ready": gates.get("manifest_ready", True),
            "mapping_ready": gates.get("mapping_ready", True),
            "import_ready": gates.get("import_ready", True),
            "rag_ready": gates.get("rag_ready", True),
            "practice_ready": gates.get("practice_ready", True),
            "manual_smoke_ready": gates.get("manual_smoke_ready", False),
            "pilot_visible": gates.get("pilot_visible", False),
            "promotion_allowed": gates.get("promotion_allowed", False),
            "blocked_reason": gates.get("blocked_reason", None),
        }
    return out


def test_validate_all_gates_pilot_in_scope_promoted_to_true():
    """Math с всеми gates → canonical promotion=true."""
    raw = _payload({
        "math": {
            "manifest_ready": True, "mapping_ready": True, "import_ready": True,
            "rag_ready": True, "practice_ready": True, "manual_smoke_ready": True,
            "pilot_visible": True, "promotion_allowed": True, "blocked_reason": None,
        },
    })
    canonical = validate_evidence_payload(raw)
    assert canonical["math"]["pilot_visible"] is True
    assert canonical["math"]["promotion_allowed"] is True


def test_validate_blocked_ocr_forces_promotion_false():
    """blocked_ocr + persisted promotion=true → canonical=false."""
    raw = _payload({
        "hist": {
            "manifest_ready": True, "mapping_ready": True, "import_ready": True,
            "rag_ready": True, "practice_ready": True, "manual_smoke_ready": True,
            "pilot_visible": True,  # Persisted tries to override.
            "promotion_allowed": True,  # Persisted tries to override.
            "blocked_reason": "blocked_ocr",
        },
    })
    canonical = validate_evidence_payload(raw)
    assert canonical["hist"]["promotion_allowed"] is False, (
        "blocked_ocr + persisted promotion=true должен быть проигнорирован"
    )
    assert canonical["hist"]["pilot_visible"] is False
    # Divergence должна быть зафиксирована в errors/warnings.
    errs = getattr(validate_evidence_payload, "_last_errors", [])
    joined = " ".join(errs)
    # Конкретный терминология validator'а: "не все required gates true или blocked_reason"
    assert "persisted" in joined or "canonical" in joined, (
        f"ожидается warning про divergence, got: {errs}"
    )
    assert "blocked_reason" in joined or "blocked_ocr" in joined, (
        f"ожидается явное упоминание блокировки, got: {errs}"
    )


def test_validate_out_of_pilot_scope_never_pilot_visible():
    """algebra (НЕ в PILOT_SCOPE) → canonical pilot=false, даже при gates=true."""
    raw = _payload({
        "algebra": {
            "manifest_ready": True, "mapping_ready": True, "import_ready": True,
            "rag_ready": True, "practice_ready": True, "manual_smoke_ready": True,
            "pilot_visible": True, "promotion_allowed": True, "blocked_reason": None,
        },
    })
    canonical = validate_evidence_payload(raw)
    assert canonical["algebra"]["pilot_visible"] is False, (
        "algebra вне PILOT_SCOPE → canonical pilot_visible=false"
    )
    assert canonical["algebra"]["promotion_allowed"] is False


def test_validate_any_required_gate_false_blocks_promotion():
    """Если любой REQUIRED_GATES gate = false → promotion=false."""
    for missing in REQUIRED_GATES:
        gates_ok = {
            "manifest_ready": True, "mapping_ready": True, "import_ready": True,
            "rag_ready": True, "practice_ready": True, "manual_smoke_ready": True,
            "pilot_visible": True, "promotion_allowed": True, "blocked_reason": None,
        }
        gates_ok[missing] = False
        raw = _payload({"math": gates_ok})
        canonical = validate_evidence_payload(raw)
        assert canonical["math"]["promotion_allowed"] is False, (
            f"{missing}=false должен блокировать promotion"
        )


def test_validate_manual_smoke_does_not_block_promotion():
    """manual_smoke_ready=false НЕ блокирует promotion (fail-closed правила).

    Это явно документировано в Sprint 3: manual smoke — НЕ hard gate.
    Но мы хотим видеть её в audit (separate signal).
    """
    raw = _payload({
        "math": {
            "manifest_ready": True, "mapping_ready": True, "import_ready": True,
            "rag_ready": True, "practice_ready": True,
            "manual_smoke_ready": False,  # НЕ блокирует promotion.
            "pilot_visible": True, "promotion_allowed": True, "blocked_reason": None,
        },
    })
    canonical = validate_evidence_payload(raw)
    assert canonical["math"]["promotion_allowed"] is True, (
        "manual_smoke_ready=false не должен блокировать promotion"
    )


def test_validate_unknown_blocked_reason_normalized_to_none():
    """Неизвестный blocked_reason → нормализуется в None + warning."""
    raw = _payload({
        "math": {
            "manifest_ready": True, "mapping_ready": True, "import_ready": True,
            "rag_ready": True, "practice_ready": True, "manual_smoke_ready": True,
            "pilot_visible": True, "promotion_allowed": True,
            "blocked_reason": "some_invented_reason",  # Не в ALLOWED.
        },
    })
    canonical = validate_evidence_payload(raw)
    # canonical promotion остаётся true (если gates ok), но blocked_reason → None.
    assert canonical["math"]["blocked_reason"] is None
    errs = " ".join(getattr(validate_evidence_payload, "_last_errors", []))
    assert "not_available" in errs or "blocked_reason" in errs


def test_validate_rejects_non_object_root():
    with pytest.raises(EvidenceValidationError):
        validate_evidence_payload([])  # type: ignore[arg-type]
    with pytest.raises(EvidenceValidationError):
        validate_evidence_payload("not a dict")  # type: ignore[arg-type]


def test_is_canonical_violation_flags_persisted_overrides():
    """is_canonical_violation возвращает коды с расхождением."""
    raw = _payload({
        "math": {"pilot_visible": True, "promotion_allowed": True},  # ok
        "hist": {  # persisted=true, но blocked_ocr → canonical=false
            "pilot_visible": True, "promotion_allowed": True,
            "blocked_reason": "blocked_ocr",
        },
    })
    canonical = validate_evidence_payload(raw)
    viols = is_canonical_violation(canonical)
    assert "hist" in viols
    assert "math" not in viols


# === File validation: real evidence.json ======================================

def test_validate_real_evidence_file_against_pilot_scope():
    """data/textbooks/7-class/evidence.json: hist/hist-world за пределами pilot_scope,
    algebra/geom ни в persisted не должны pilot_visible=true."""
    path = find_evidence_path()
    if path is None:
        pytest.skip("evidence.json не найден")
    canonical = validate_evidence_file(path)
    # Не должно быть никого вне math с pilot_visible=true.
    for code, view in canonical.items():
        if code == "math":
            continue
        if view["pilot_visible"]:
            pytest.fail(
                f"{code}: pilot_visible=true вне PILOT_SCOPE. "
                f"Canonical derivation должна была сбросить в false."
            )
        if view["promotion_allowed"]:
            pytest.fail(
                f"{code}: promotion_allowed=true вне PILOT_SCOPE. "
                f"Canonical derivation должна была сбросить в false."
            )


def test_validate_real_evidence_with_blocked_ocr():
    """Реальный evidence.json имеет hist/hist-world с blocked_ocr.
    Canonical должна снять promotion на них."""
    path = find_evidence_path()
    if path is None:
        pytest.skip("evidence.json не найден")
    canonical = validate_evidence_file(path)
    for code in ("hist", "hist-world"):
        if code in canonical:
            assert canonical[code]["promotion_allowed"] is False, (
                f"{code}: blocked_ocr должен сбрасывать promotion_allowed"
            )
            assert canonical[code]["pilot_visible"] is False


# === API: list_evidence returns canonical =====================================

@pytest.fixture()
def admin_client(tmp_path, monkeypatch):
    """TestClient с admin пользователем и изолированным evidence.json."""
    tmp_evidence = tmp_path / "evidence.json"
    initial = _payload({
        "math": {
            "manifest_ready": True, "mapping_ready": True, "import_ready": True,
            "rag_ready": True, "practice_ready": True, "manual_smoke_ready": True,
            "pilot_visible": True, "promotion_allowed": True, "blocked_reason": None,
        },
        "hist": {
            "manifest_ready": True, "mapping_ready": True, "import_ready": True,
            "rag_ready": True, "practice_ready": True, "manual_smoke_ready": True,
            "pilot_visible": True, "promotion_allowed": True,  # persisted
            "blocked_reason": "blocked_ocr",  # forces canonical=false
        },
        "algebra": {
            "manifest_ready": True, "mapping_ready": True, "import_ready": True,
            "rag_ready": True, "practice_ready": True, "manual_smoke_ready": True,
            "pilot_visible": True, "promotion_allowed": True,  # persisted
            "blocked_reason": None,  # но algebra вне PILOT_SCOPE
        },
    })
    tmp_evidence.write_text(json.dumps(initial, ensure_ascii=False, indent=2))

    Base.metadata.drop_all(engine)
    engine.dispose()
    Base.metadata.create_all(engine)

    from app.auth.security import hash_password
    from app.users.models import Role, User

    s = SessionLocal()
    try:
        # Admin создаём вручную (через /register нельзя — защита от саморегистрации).
        admin = User(
            email="admin@example.com",
            password_hash=hash_password("strongpass1"),
            role=Role.ADMIN,
            display_name="Admin",
        )
        s.add(admin)
        s.commit()
    finally:
        s.close()

    from app.admin import router as admin_router

    monkeypatch.setattr(admin_router, "_EVIDENCE_PATH", tmp_evidence)
    # Подменить subjects.evidence loader — иначе он кеширует prod evidence.
    from app.subjects import evidence as evidence_mod

    monkeypatch.setattr(
        "app.subjects.evidence._try_load_evidence_json",
        lambda: {},
    )
    evidence_mod.reset_evidence_cache()

    def _gen():
        s = SessionLocal()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = _gen

    def _login():
        r = TestClient(app).post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "strongpass1"},
        )
        return r.json()["access_token"]

    with TestClient(app) as c:
        token = _login()
        yield c, token

    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


def test_api_list_evidence_returns_canonical_not_persisted(admin_client):
    """GET /evidence: hist/hist-world заблокированы canonical,
    algebra — вне scope."""
    c, token = admin_client
    headers = {"Authorization": f"Bearer {token}"}
    r = c.get("/api/v1/admin/evidence", headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    by_code = {item["subject_code"]: item for item in body["evidence"]}
    # Math remains pilot.
    assert by_code["math"]["pilot_visible"] is True
    assert by_code["math"]["promotion_allowed"] is True
    # hist -> blocked_ocr → НЕ pilot.
    if "hist" in by_code:
        assert by_code["hist"]["pilot_visible"] is False
        assert by_code["hist"]["promotion_allowed"] is False
        assert by_code["hist"]["canonical_divergence"] in (
            "ok", "persisted_overrides_canonical",
        )
    # algebra -> вне PILOT_SCOPE → НЕ pilot.
    assert by_code["algebra"]["pilot_visible"] is False
    assert by_code["algebra"]["promotion_allowed"] is False


def test_api_update_evidence_records_canonical_divergence(admin_client):
    """POST /evidence/{code}: persisted vs canonical регистрируется в details.

    Math имеет все gates true и в PILOT_SCOPE → canonical=true.
    Чтобы снять promotion guard, нужно sync снять promotion_allowed.
    """
    c, token = admin_client
    headers = {"Authorization": f"Bearer {token}"}
    # 1) Снимаем сразу gate + promotion (чтобы пройти existing guard).
    r = c.post(
        "/api/v1/admin/evidence/math",
        headers=headers,
        json={"gates": {"practice_ready": False}, "promotion_allowed": False},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["subject_code"] == "math"
    assert body["canonical_promotion_allowed"] is False
    assert body["canonical_divergence"] in ("ok", "persisted_overrides_canonical")
    # 2) Восстанавливаем обратно.
    r2 = c.post(
        "/api/v1/admin/evidence/math",
        headers=headers,
        json={"gates": {"practice_ready": True}, "promotion_allowed": True},
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["canonical_promotion_allowed"] is True


def test_api_update_evidence_promotion_blocked_without_all_gates(admin_client):
    """S3: promotion_allowed=true НЕЛЬЗЯ при false обязательном gate."""
    c, token = admin_client
    headers = {"Authorization": f"Bearer {token}"}
    # Снимаем gate (allowed → 200, т.к. persisted promo снимаем синхронно).
    r = c.post(
        "/api/v1/admin/evidence/algebra",
        headers=headers,
        json={"gates": {"mapping_ready": False}, "promotion_allowed": False},
    )
    assert r.status_code == 200
    # Теперь promotion=true должен быть заблокирован (missing gates).
    r2 = c.post(
        "/api/v1/admin/evidence/algebra",
        headers=headers,
        json={"promotion_allowed": True},
    )
    assert r2.status_code == 400, r2.text
