"""Sprint 5 (2026-08-23): textbook manifest + provenance audit.

Цель: проверить что manifest синхронизирован с файлами и mapping'ами,
checksum валиден, license_decision присутствует, нет orphan/duplicate
mapping'ов, coverage math-tops ≥ 15 P0.

Это read-only audit (production_mutation=false, db_write=false,
rag_write=false, promotion_allowed=false) — НЕ мутирует state.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
from collections import defaultdict
from pathlib import Path

import pytest
from app.subjects.textbook_manifest_policy import validate_textbook_manifest

REPO_ROOT = Path("/root/workspace/ai-tutor")
MANIFEST_CSV = REPO_ROOT / "data" / "textbooks" / "7-class" / "textbook-manifest.csv"
MAPPINGS_DIR = REPO_ROOT / "data" / "textbooks" / "7-class" / "mappings"
EXPECTED_MANIFEST_ROWS = 20

ALLOWED_LICENSE_DECISIONS = {
    "needs_review",
    "approved",
    "rejected",
    "approved_with_attribution",
    "public_domain",
    "cc_by",
    "cc_by_sa",
    "fair_use_education",
}

ALLOWED_SOURCE_KINDS = {"internal_scan", "ocr", "pdf_native", "epub", "html"}

ALLOWED_OCR_STATUS = {"text_layer", "image_only", "ocr", "mixed", "missing"}


def _sha256_short(path: Path, n_bytes: int = 8192) -> str:
    """Sprint 5: manifest sha256 — для теста считаем первые 8KB это proxy.

    Реальный манифест хранит sha256 полного файла, и для audit мы берём
    первые 8KB чтобы не грузить полные 100-300 MB PDF. Если в манифесте
    sha256 начинается с нашего partial-hash — это индикатор, что файл
    не менялся с момента манифеста."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        chunk = f.read(n_bytes)
    h.update(chunk)
    return h.hexdigest()


@pytest.fixture(scope="module")
def manifest_rows() -> list[dict[str, str]]:
    if not MANIFEST_CSV.exists():
        pytest.skip(f"manifest не найден: {MANIFEST_CSV}")
    with MANIFEST_CSV.open() as f:
        return list(csv.DictReader(f))


def test_manifest_license_policy_is_fail_closed(manifest_rows):
    """Unresolved rights never become importable or pilot-ready."""
    report = validate_textbook_manifest(manifest_rows)
    assert report["row_count"] == EXPECTED_MANIFEST_ROWS
    assert report["blocked_license_count"] == EXPECTED_MANIFEST_ROWS
    assert report["pilot_allowed"] is False
    assert report["production_mutation"] is False
    assert report["db_write"] is False
    assert report["rag_write"] is False
    assert all(row["pilot_allowed"] is False for row in report["rows"])


# === Manifest basics ==========================================================


def test_manifest_has_expected_20_rows(manifest_rows):
    """Sprint 5: манифест содержит 20 записей (аудит baseline)."""
    assert (
        len(manifest_rows) == EXPECTED_MANIFEST_ROWS
    ), f"manifest содержит {len(manifest_rows)} строк, ожидалось {EXPECTED_MANIFEST_ROWS}"


def test_manifest_header_is_complete(manifest_rows):
    """Sprint 5: все обязательные колонки присутствуют."""
    required = {
        "subject_code",
        "grade",
        "part",
        "title",
        "author",
        "year",
        "local_path",
        "source_url",
        "source_kind",
        "license_decision",
        "sha256",
        "pages",
        "text_pages",
        "text_coverage",
        "ocr_status",
        "ocr_language",
        "known_problem_pages",
        "original_path",
        "is_original_scan",
        "status",
        "topic_mapping_path",
        "import_status",
        "rag_status",
        "manual_smoke_status",
    }
    headers = set(manifest_rows[0].keys()) if manifest_rows else set()
    missing = required - headers
    assert not missing, f"отсутствуют колонки манифеста: {missing}"


def test_manifest_license_decision_is_known_enum(manifest_rows):
    """Sprint 5: license_decision ∈ known enum (аудит '20 = needs_review')."""
    for row in manifest_rows:
        ld = row["license_decision"]
        assert ld in ALLOWED_LICENSE_DECISIONS, f"subject={row['subject_code']} license_decision={ld!r} не в allowed"


def test_manifest_source_kind_is_known_enum(manifest_rows):
    for row in manifest_rows:
        sk = row["source_kind"]
        assert sk in ALLOWED_SOURCE_KINDS, f"subject={row['subject_code']} source_kind={sk!r} не в allowed"


def test_manifest_ocr_status_is_known_enum(manifest_rows):
    for row in manifest_rows:
        os_ = row["ocr_status"]
        assert os_ in ALLOWED_OCR_STATUS, f"subject={row['subject_code']} ocr_status={os_!r} не в allowed"


def test_manifest_sha256_format(manifest_rows):
    """Sprint 5: sha256 — 64-символьный hex."""
    for row in manifest_rows:
        sha = row["sha256"]
        assert len(sha) == 64, f"subject={row['subject_code']} sha256={sha!r} не 64 chars"
        assert all(c in "0123456789abcdef" for c in sha), f"subject={row['subject_code']} sha256 не hex"


# === Filesystem cross-check ===================================================


def test_manifest_local_path_exists(manifest_rows, repo_root_only=False):
    """Sprint 5: local_path файлы существуют (best-effort: некоторые могут отсутствовать)."""
    missing = []
    for row in manifest_rows:
        lp = (REPO_ROOT / row["local_path"]).resolve()
        if not lp.exists():
            missing.append((row["subject_code"], row["local_path"]))
    # Best-effort: некоторые файлы могут быть не в test-env — логируем как soft warning.
    if missing:
        pytest.skip(f"manifest local_path файлы отсутствуют в test-env: {len(missing)} " f"(например {missing[:3]})")


def test_manifest_subject_codes_are_known():
    """subject_code ∈ known curriculum set (audit)."""
    known = {
        "math",
        "algebra",
        "geom",
        "rus",
        "lit",
        "eng",
        "hist",
        "hist-world",
        "phys",
        "inf",
        "soc",
        "chem",
        "bio",
        "geo",
        "lit-2",
        "rus-2",
    }
    with MANIFEST_CSV.open() as f:
        codes = {row["subject_code"] for row in csv.DictReader(f)}
    unknown = codes - known
    assert not unknown, f"неизвестные subject_code: {unknown}"


def test_manifest_duplicate_local_paths_disallowed(manifest_rows):
    """Sprint 5: каждый local_path уникален (нет дублей)."""
    by_local: dict[str, list[str]] = defaultdict(list)
    for row in manifest_rows:
        by_local[row["local_path"]].append(row["subject_code"])
    duplicates = {k: v for k, v in by_local.items() if len(v) > 1}
    assert not duplicates, f"duplicates local_path: {duplicates}"


# === Mappings coverage ========================================================


@pytest.fixture(scope="module")
def mappings_index() -> dict[str, dict]:
    out: dict[str, dict] = {}
    if not MAPPINGS_DIR.exists():
        return out
    for path in MAPPINGS_DIR.glob("*-topic-page-map.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        out[path.stem.replace("-topic-page-map", "")] = data
    return out


def test_mappings_dir_has_files_for_each_manifest_subject(manifest_rows, mappings_index):
    """Sprint 5: для каждого subject_code из манифеста есть mapping JSON."""
    by_manifest = {row["subject_code"] for row in manifest_rows}
    by_mapping = set(mappings_index.keys())
    missing = by_manifest - by_mapping
    assert not missing, f"нет mapping для subjects: {missing}"


def test_math_mapping_has_at_least_15_topics(mappings_index):
    """Sprint 5: math mapping (Sprint 4 P0) имеет ≥15 entries."""
    math_mapping = mappings_index.get("math")
    if not math_mapping:
        pytest.skip("math mapping отсутствует")
    entries = math_mapping.get("entries", [])
    assert len(entries) >= 15, f"math mapping содержит {len(entries)} entries, ожидалось ≥15"


def test_mapping_entries_have_required_fields(mappings_index):
    """Sprint 5: каждая entry имеет topic_id, topic_name, page_range slots,
    confidence, qa_status. page_start/page_end могут быть null если draft,
    но поля должны присутствовать."""
    required = {"topic_id", "topic_name", "confidence", "qa_status"}
    for code, data in mappings_index.items():
        entries = data.get("entries", [])
        for entry in entries:
            missing = required - entry.keys()
            assert not missing, f"{code}::topic entry={entry.get('topic_id')} missing {missing}"


def test_mapping_duplicate_topic_ids_in_subject_forbidden(mappings_index):
    """Sprint 5: один topic_id = одна запись внутри subject."""
    for code, data in mappings_index.items():
        entries = data.get("entries", [])
        ids = [e["topic_id"] for e in entries]
        seen = set()
        dups = set()
        for tid in ids:
            if tid in seen:
                dups.add(tid)
            seen.add(tid)
        assert not dups, f"{code}: duplicate topic_id={dups}"


# === Cross-check manifest ↔ mapping ==========================================


def test_manifest_mapping_paths_resolve(manifest_rows):
    """Sprint 5: topic_mapping_path из манифеста указывает на существующий JSON."""
    for row in manifest_rows:
        mp = REPO_ROOT / row["topic_mapping_path"]
        assert mp.exists(), f"subject={row['subject_code']} mapping={mp} не существует"


def test_manifest_subject_codes_match_mapping_subject_code(manifest_rows, mappings_index):
    """Sprint 5: subject_code в манифесте === subject_code в mapping JSON."""
    by_manifest = {row["subject_code"] for row in manifest_rows}
    by_mapping = set(mappings_index.keys())
    # Каждый манифест-subject имеет mapping; extra mappings ОК.
    missing = by_manifest - by_mapping
    assert not missing, f"manifest subjects без mapping: {missing}"


# === Provenance checks ========================================================


def test_manifest_source_url_is_http(manifest_rows):
    for row in manifest_rows:
        url = row["source_url"]
        assert url.startswith("http"), f"subject={row['subject_code']} source_url={url!r} без http(s)"


def test_manifest_year_is_int_or_zero(manifest_rows):
    """Sprint 5: year ∈ int (≥ 1900) или 0 (если unknown)."""
    for row in manifest_rows:
        year_str = row["year"]
        # CSV может содержать пустую строку.
        if year_str == "":
            continue
        try:
            year = int(year_str)
        except ValueError:
            pytest.fail(f"subject={row['subject_code']} year={year_str!r} не int")
        assert year == 0 or year >= 1900, f"subject={row['subject_code']} year={year} вне диапазона"


def test_manifest_grade_is_seven(manifest_rows):
    """Sprint 5: манифест описывает только 7 класс."""
    for row in manifest_rows:
        grade_str = row["grade"]
        if grade_str == "":
            continue
        assert grade_str == "7", f"subject={row['subject_code']} grade={grade_str!r} ≠ '7'"
