from __future__ import annotations

from scripts.targeted_deploy_manifest import classify_paths, build_manifest


def test_classify_backend_runtime_change_requires_backup_and_backend_tests() -> None:
    manifest = build_manifest(["apps/backend/app/ai/service.py"])

    assert manifest["services"] == ["backend"]
    assert manifest["backup_required"] is True
    assert any("test_ai_output_contract.py" in cmd for cmd in manifest["required_tests"])
    assert any("docker compose build backend" in cmd for cmd in manifest["deploy_steps"])


def test_classify_frontend_runtime_change_requires_frontend_gates() -> None:
    manifest = build_manifest(["apps/frontend/app/subjects/page.tsx"])

    assert manifest["services"] == ["frontend"]
    assert manifest["backup_required"] is True
    assert "cd apps/frontend && npx tsc --noEmit" in manifest["required_tests"]
    assert any("docker compose build frontend" in cmd for cmd in manifest["deploy_steps"])


def test_classify_docs_only_change_needs_no_backup_or_deploy() -> None:
    manifest = build_manifest(["docs/README.md"])

    assert manifest["services"] == ["docs"]
    assert manifest["backup_required"] is False
    assert manifest["deploy_steps"] == []


def test_classify_mixed_backend_frontend_change_orders_services() -> None:
    manifest = build_manifest([
        "apps/frontend/app/admin/page.tsx",
        "apps/backend/app/admin/router.py",
    ])

    assert manifest["services"] == ["backend", "frontend"]
    assert manifest["backup_required"] is True
    assert any("pytest" in cmd for cmd in manifest["required_tests"])
    assert any("npx tsc" in cmd for cmd in manifest["required_tests"])


def test_classify_paths_marks_unknown_as_manual_review() -> None:
    classified = classify_paths(["deploy/prometheus/alerts.yml", "scripts/release_preflight.sh"])

    assert classified["ops"] == ["deploy/prometheus/alerts.yml", "scripts/release_preflight.sh"]
