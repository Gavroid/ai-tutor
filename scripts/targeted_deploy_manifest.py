"""Classify changed files into targeted deploy requirements.

This helper is intentionally offline/read-only. It does not connect to
production and does not execute deploys.
"""
from __future__ import annotations

import argparse
import json
from collections import OrderedDict
from pathlib import PurePosixPath
from typing import Iterable

_SERVICE_ORDER = ["backend", "frontend", "ops", "docs"]


def classify_paths(paths: Iterable[str]) -> dict[str, list[str]]:
    classified: dict[str, list[str]] = {key: [] for key in _SERVICE_ORDER}
    for raw in paths:
        path = str(PurePosixPath(raw))
        if path.startswith("apps/backend/"):
            classified["backend"].append(path)
        elif path.startswith("apps/frontend/"):
            classified["frontend"].append(path)
        elif path.startswith("docs/") or path.startswith(".hermes/plans/"):
            classified["docs"].append(path)
        else:
            classified["ops"].append(path)
    return {key: value for key, value in classified.items() if value}


def _ordered_services(classified: dict[str, list[str]]) -> list[str]:
    return [service for service in _SERVICE_ORDER if service in classified]


def _required_tests(services: list[str], paths: list[str]) -> list[str]:
    tests: list[str] = []
    if "backend" in services:
        if any("app/ai/" in path for path in paths):
            tests.append("cd apps/backend && .venv/bin/pytest tests/test_ai_output_contract.py tests/test_health.py -q")
        elif any("app/admin/" in path for path in paths):
            tests.append("cd apps/backend && .venv/bin/pytest tests/test_admin.py tests/test_health.py -q")
        elif any("app/parents/" in path for path in paths):
            tests.append("cd apps/backend && .venv/bin/pytest tests/test_parent_privacy_stage23.py tests/test_health.py -q")
        elif any("app/teacher/" in path for path in paths):
            tests.append("cd apps/backend && .venv/bin/pytest tests/test_teacher.py tests/test_health.py -q")
        else:
            tests.append("cd apps/backend && .venv/bin/pytest tests/test_health.py -q")
    if "frontend" in services:
        tests.append("cd apps/frontend && npx tsc --noEmit")
    if "ops" in services:
        tests.append("manual review required for ops/deploy/script changes")
    if not tests and services == ["docs"]:
        tests.append("git diff --check")
    return tests


def _deploy_steps(services: list[str]) -> list[str]:
    steps: list[str] = []
    if "backend" in services:
        steps.append("docker compose build backend && docker compose up -d --no-deps backend")
    if "frontend" in services:
        steps.append("docker compose build frontend && docker compose up -d --no-deps frontend")
    if "ops" in services:
        steps.append("manual targeted ops deploy/reload only after review")
    return steps


def build_manifest(paths: Iterable[str]) -> dict[str, object]:
    path_list = list(paths)
    classified = classify_paths(path_list)
    services = _ordered_services(classified)
    runtime_services = [service for service in services if service != "docs"]
    return {
        "services": services,
        "classified_paths": classified,
        "backup_required": bool(runtime_services),
        "required_tests": _required_tests(services, path_list),
        "deploy_steps": _deploy_steps(services),
        "smoke_steps": [
            "curl -sk -w '\\nREADY_HTTP=%{http_code}\\n' https://localhost/ready",
            "curl -sk -w '\\nHEALTH_HTTP=%{http_code}\\n' https://localhost/health",
        ] if runtime_services else [],
        "notes": [
            "Run backup/offsite before runtime production mutation." if runtime_services else "Docs-only change: no production deploy required.",
            "Do not advance .mvp-rescue-commit for ad-hoc targeted deploys unless full marker workflow is intentionally executed.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    manifest = build_manifest(args.paths)
    services = manifest["services"]
    service_text = ", ".join(services) if isinstance(services, list) else "none"
    if args.json:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
    else:
        print(f"services: {service_text}")
        print(f"backup_required: {manifest['backup_required']}")
        for test in manifest["required_tests"]:  # type: ignore[index]
            print(f"test: {test}")
        for step in manifest["deploy_steps"]:  # type: ignore[index]
            print(f"deploy: {step}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
