from __future__ import annotations

from scripts.targeted_deploy_manifest import build_manifest


def test_runtime_manifest_requires_scope_backup_restore_and_smoke_evidence() -> None:
    manifest = build_manifest(["apps/backend/app/subjects/evidence.py"])

    assert manifest["backup_required"] is True
    assert manifest["release_gate"] == "math_only_scope_and_external_evidence_required"
    assert "scope_snapshot" in manifest["required_evidence"]
    assert "backup_offsite" in manifest["required_evidence"]
    assert "restore_drill" in manifest["required_evidence"]
    assert "student_smoke" in manifest["required_evidence"]
    assert manifest["can_deploy"] is False


def test_docs_only_manifest_remains_non_deploying() -> None:
    manifest = build_manifest(["docs/README.md"])

    assert manifest["can_deploy"] is True
    assert manifest["required_evidence"] == []
