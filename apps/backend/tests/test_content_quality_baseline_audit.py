from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any, cast

from scripts.content_quality_baseline_audit import (
    build_content_quality_baseline,
    format_markdown,
    overlay_production_readiness,
)


def _subjects(report: dict[str, object]) -> list[dict[str, Any]]:
    return cast(list[dict[str, Any]], report["subjects"])


def test_content_quality_baseline_covers_all_seeded_subjects_and_topics() -> None:
    report = build_content_quality_baseline()
    subjects = _subjects(report)

    assert report["ok"] is True
    assert report["production_mutation"] is False
    assert report["db_write"] is False
    assert report["rag_write"] is False
    assert report["promotion_allowed"] is False
    assert report["manual_smoke_ready"] is False
    # S1.1 (2026-09-01): curriculum_7_class теперь 16 предметов (добавлены
    # chem/hist-world/lit-2/rus-2 согласно stakeholder D2.1). Topic totals
    # суммируются из curriculum sections итого = 263.
    assert report["subject_count"] == 16
    assert report["topic_count"] == 263
    assert len(subjects) == 16
    assert all("route_ready" in subject for subject in subjects)
    assert all("source_ready" in subject for subject in subjects)
    assert all("practice_ready" in subject for subject in subjects)
    assert all(subject["manual_smoke_ready"] is False for subject in subjects)
    assert all(subject["promotion_allowed"] is False for subject in subjects)


def test_content_quality_baseline_has_no_technical_gate_failures() -> None:
    report = build_content_quality_baseline()

    assert report["technical_issue_count"] == 0
    assert report["issue_counts"] == {}
    assert all(subject["technical_issue_count"] == 0 for subject in _subjects(report))


def test_content_quality_baseline_flags_textbook_grade_work_without_breaking_mvp() -> None:
    report = build_content_quality_baseline()
    by_code = {subject["code"]: subject for subject in _subjects(report)}

    assert by_code["math"]["priority"] == "P0_fill_coverage"
    assert "no_local_source_manifest" in by_code["math"]["quality_flags"]
    assert by_code["algebra"]["priority"] == "P0_fill_coverage"
    assert "no_local_source_manifest" in by_code["algebra"]["quality_flags"]
    assert by_code["phys"]["priority"] == "P1_textbook_grade_upgrade"
    assert "needs_verified_subject_sources" in by_code["phys"]["quality_flags"]
    assert by_code["eng"]["priority"] == "P1_textbook_grade_upgrade"
    assert by_code["geom"]["priority"] in {"P2_depth_upgrade", "P3_monitor"}


def test_overlay_production_readiness_keeps_readiness_separate_from_quality_flags() -> None:
    report = build_content_quality_baseline()
    production_subjects = [
        {
            "code": subject["code"],
            "mvp_status": "mvp_ready",
            "route_ready": True,
            "rag_ready": True,
            "practice_ready": True,
            "topic_count": subject["topic_count"],
            "route_topic_count": subject["topic_count"],
            "source_topic_count": subject["topic_count"],
            "practice_topic_count": subject["topic_count"],
        }
        for subject in _subjects(report)
    ]

    enriched = overlay_production_readiness(report, production_subjects)
    enriched_subjects = _subjects(enriched)

    # S1.1 (2026-09-01): overlay теперь покрывает все 16 subjects (добавлены
    # chem/hist-world/lit-2/rus-2 согласно stakeholder D2.1).
    assert enriched["production_subject_count"] == 16
    assert enriched["production_readiness_problems"] == []
    assert enriched_subjects[0]["production_mvp_status"] == "mvp_ready"
    assert enriched_subjects[0]["quality_flags"] == _subjects(report)[0]["quality_flags"]


def test_content_quality_markdown_is_safe_summary_not_answer_dump() -> None:
    report = build_content_quality_baseline()
    markdown = format_markdown(report)

    assert markdown.startswith("# AI-Tutor Content Quality Baseline")
    assert "| Subject | Topics | Fallbacks | Sources | Source Mode | Technical Issues | Priority | Flags |" in markdown
    assert "Promotion allowed: `False`" in markdown
    assert "P1_textbook_grade_upgrade" in markdown
    assert "correct_answer" not in markdown
    assert "<think>" not in markdown


def test_content_quality_cli_runs_without_project_env_or_secrets() -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    env = {
        "PATH": os.environ["PATH"],
        "PYTHONPATH": ".",
        "HOME": os.environ.get("HOME", "/tmp"),
    }

    result = subprocess.run(
        [str(backend_dir / ".venv/bin/python"), "scripts/content_quality_baseline_audit.py", "--json"],
        cwd=backend_dir,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["mode"] == "content_quality_baseline_local_read_only"
    assert report["production_mutation"] is False
    assert report["db_write"] is False
    assert report["rag_write"] is False
    assert report["promotion_allowed"] is False
