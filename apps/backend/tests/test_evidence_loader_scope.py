from __future__ import annotations

import json
from pathlib import Path

from app.subjects import evidence


def test_evidence_loader_canonicalizes_pilot_scope_and_blocked_reason(
    tmp_path: Path,
    monkeypatch,
) -> None:
    payload = {
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
            "mapping_ready": True,
            "import_ready": True,
            "rag_ready": True,
            "practice_ready": True,
            "manual_smoke_ready": True,
            "pilot_visible": True,
            "promotion_allowed": True,
            "blocked_reason": None,
        },
        "hist": {
            "manifest_ready": True,
            "mapping_ready": True,
            "import_ready": True,
            "rag_ready": True,
            "practice_ready": True,
            "manual_smoke_ready": True,
            "pilot_visible": True,
            "promotion_allowed": True,
            "blocked_reason": "blocked_ocr",
        },
    }
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    def load() -> dict[str, evidence.SubjectEvidence] | None:
        return evidence._load_evidence_file(path)

    monkeypatch.setattr(evidence, "_try_load_evidence_json", load)
    evidence.reset_evidence_cache()

    assert evidence.get_evidence_for("math").pilot_visible is True
    # Sprint 3.9.3 (2026-08-22): algebra В PILOT_SCOPE (все 16 promoted),
    # canonical derivation возвращает promotion_allowed=True.
    assert evidence.get_evidence_for("algebra").pilot_visible is True
    assert evidence.get_evidence_for("algebra").promotion_allowed is True
    # hist заблокирован canonical (blocked_ocr) → promotion_allowed=False.
    assert evidence.get_evidence_for("hist").pilot_visible is False
    assert evidence.get_evidence_for("hist").promotion_allowed is False
