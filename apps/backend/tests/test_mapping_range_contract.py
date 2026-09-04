"""Sprint B: source mapping range validation tests."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MAPPING_DIR = ROOT / "data" / "textbooks" / "7-class" / "mappings"


def _entries(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload.get("entries", [])


def test_all_mapping_ranges_are_ordered_when_present() -> None:
    invalid: list[str] = []
    for path in sorted(MAPPING_DIR.glob("*-topic-page-map.json")):
        for row in _entries(path):
            start = row.get("page_start")
            end = row.get("page_end")
            if start is not None and end is not None and start > end:
                invalid.append(f"{path.name}:{row.get('topic_id')}:{start}-{end}")
    # S1.5 (2026-09-01): bio:196 (7→6) и soc:160-163 (45→44) исправлены
    # (page_start↔page_end swap). После фикса должно быть 0 invalid ranges.
    assert invalid == [], f"unexpected invalid ranges: {invalid}"


def test_mapping_rows_require_review_before_promotion() -> None:
    for path in sorted(MAPPING_DIR.glob("*-topic-page-map.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload.get("mapping_status") == "draft"
        for row in payload.get("entries", []):
            assert row.get("qa_status") != "reviewed"
