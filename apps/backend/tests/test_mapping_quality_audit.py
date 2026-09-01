from pathlib import Path

from scripts.mapping_quality_audit import audit_mapping_dir


def test_mapping_quality_audit_reports_known_inventory_gaps() -> None:
    root = Path(__file__).resolve().parents[3]
    result = audit_mapping_dir(root / "data" / "textbooks" / "7-class")
    # S1.5 (2026-09-01): bio:196 и soc:160-163 были page_start > page_end;
    # починены swap. До этого теста: invalid_ranges=5. После: invalid_ranges=0.
    assert result["mapping_rows"] == 280
    assert result["missing_ranges"] == 179
    assert result["invalid_ranges"] == 0
    assert result["reviewed_rows"] == 0
    assert result["read_only"] is True
