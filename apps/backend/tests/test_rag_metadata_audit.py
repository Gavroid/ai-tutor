from __future__ import annotations

import json

from scripts.rag_metadata_audit import audit_chunk_metadata, audit_rows, summarize_audit


def _row(subject_code: str, topic_id: int, metadata: dict[str, object], *, material_subject_code: str | None = None) -> dict[str, object]:
    return {
        "chunk_id": 1,
        "material_id": 10,
        "material_title": metadata.get("material_title", "Source material"),
        "material_topic_id": topic_id,
        "material_subject_code": material_subject_code or subject_code,
        "metadata_json": json.dumps(metadata, ensure_ascii=False),
    }


def test_rag_metadata_contract_accepts_topic_scoped_chunk():
    problems = audit_chunk_metadata(
        _row(
            "algebra",
            34,
            {
                "subject_id": 4,
                "subject_code": "algebra",
                "topic_id": 34,
                "topic_name": "числовые выражения",
                "material_title": "IM Algebra 1 Unit 2",
                "source_title": "Illustrative Mathematics Algebra 1",
                "source_url": "https://im.kendallhunt.com/HS/students/1/index.html",
                "source_section": "Unit 2 Linear Equations, Inequalities, and Systems",
                "license": "CC BY 4.0",
                "attribution": "Based on IM® K–12 Math authored by Illustrative Mathematics®. Used under a CC BY 4.0 license.",
            },
        ),
        expected_subject_code="algebra",
    )

    assert problems == []


def test_rag_metadata_contract_rejects_missing_required_metadata():
    problems = audit_chunk_metadata(
        _row("algebra", 34, {"topic_id": 34, "subject_code": "algebra"}),
        expected_subject_code="algebra",
    )

    assert "missing:topic_name" in problems
    assert "missing:source_title" in problems
    assert "missing:source_section_or_page" in problems
    assert "missing:license" in problems
    assert "missing:attribution" in problems


def test_rag_metadata_contract_rejects_material_topic_mismatch():
    problems = audit_chunk_metadata(
        _row(
            "algebra",
            34,
            {
                "subject_code": "algebra",
                "topic_id": 52,
                "topic_name": "способ сложения",
                "source_title": "Illustrative Mathematics Algebra 1",
                "source_section": "Unit 2",
                "license": "CC BY 4.0",
                "attribution": "IM attribution",
            },
        ),
        expected_subject_code="algebra",
    )

    assert "topic_id_mismatch:metadata=52 material=34" in problems


def test_rag_metadata_contract_rejects_geometry_chunk_counting_as_algebra():
    problems = audit_chunk_metadata(
        _row(
            "algebra",
            34,
            {
                "subject_id": 5,
                "subject_code": "geometry",
                "topic_id": 53,
                "topic_name": "прямая, отрезок, луч, угол",
                "material_title": "IM Geometry Unit 1",
                "source_title": "Illustrative Mathematics Geometry",
                "source_section": "Unit 1 Constructions and Rigid Transformations",
                "license": "CC BY 4.0",
                "attribution": "Based on IM® Geometry authored by Illustrative Mathematics®. Used under a CC BY 4.0 license.",
            },
        ),
        expected_subject_code="algebra",
    )

    assert "subject_code_mismatch:metadata=geometry expected=algebra" in problems
    assert "topic_id_mismatch:metadata=53 material=34" in problems
    assert any(problem.startswith("source_subject_mismatch") for problem in problems)


def test_rag_metadata_audit_summary_counts_good_and_bad_rows():
    rows = [
        _row(
            "algebra",
            34,
            {
                "subject_code": "algebra",
                "topic_id": 34,
                "topic_name": "числовые выражения",
                "source_title": "Beginning and Intermediate Algebra",
                "source_section": "0.3 Order of Operations",
                "license": "CC BY 3.0",
                "attribution": "Wallace attribution",
            },
        ),
        _row("algebra", 35, {"subject_code": "geometry", "topic_id": 53}),
    ]

    findings = audit_rows(rows, expected_subject_code="algebra")
    summary = summarize_audit(findings)

    assert summary["rows_checked"] == 2
    assert summary["ok_rows"] == 1
    assert summary["bad_rows"] == 1
    assert summary["problems"]["missing:topic_name"] == 1
    assert summary["problems"]["subject_code_mismatch:metadata=geometry expected=algebra"] == 1


def test_rag_metadata_cli_can_audit_known_good_bad_fixture(tmp_path, capsys):
    from scripts import rag_metadata_audit
    import sys

    fixture = tmp_path / "rows.json"
    fixture.write_text(
        json.dumps(
            [
                _row(
                    "algebra",
                    34,
                    {
                        "subject_code": "algebra",
                        "topic_id": 34,
                        "topic_name": "числовые выражения",
                        "source_title": "Beginning and Intermediate Algebra",
                        "source_section": "0.3 Order of Operations",
                        "license": "CC BY 3.0",
                        "attribution": "Wallace attribution",
                    },
                ),
                _row("algebra", 35, {"subject_code": "geometry", "topic_id": 53}),
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    old_argv = sys.argv[:]
    sys.argv = ["rag_metadata_audit", "--subject-code", "algebra", "--input-json", str(fixture), "--json"]
    try:
        result = rag_metadata_audit.main()
    finally:
        sys.argv = old_argv

    output = json.loads(capsys.readouterr().out)
    assert result == 1
    assert output["summary"]["rows_checked"] == 2
    assert output["summary"]["ok_rows"] == 1
    assert output["summary"]["bad_rows"] == 1
