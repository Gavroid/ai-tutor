"""Temporary fetch/extract probe for exact Algebra source assets.

Fetches exact approved assets into a temporary directory, extracts text, and
validates section/topic terms. Does not write source files into the repo, import
DB rows, create RAG chunks, mutate production, or promote Algebra.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import tempfile
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any, Sequence, cast

from pypdf import PdfReader

from scripts.algebra_source_asset_manifest import build_asset_manifest

_REQUIRED_TERMS_BY_TOPIC: dict[int, tuple[str, ...]] = {
    34: ("Order", "Operations"),
    35: ("Properties", "Algebra"),
    36: ("Linear", "Equations"),
    37: ("Unit 2", "Linear Equations"),
    38: ("Unit 4", "Functions"),
    39: ("Unit 4", "Functions"),
    40: ("Variation",),
    41: ("Exponent",),
    42: ("Exponent",),
    43: ("Polynomials",),
    44: ("Polynomials",),
    45: ("Polynomials",),
    46: ("Multiply", "Polynomials"),
    47: ("Multiply", "Polynomials"),
    48: ("Special", "Products"),
    49: ("Unit 2", "Linear Equations"),
    50: ("Unit 2", "Systems"),
    51: ("Unit 2", "Systems"),
    52: ("Unit 2", "Systems"),
}


def build_probe_plan(*, topic_ids: Sequence[int] | None = None) -> list[dict[str, object]]:
    """Return exact asset rows selected for fetch/extract probing."""
    manifest = build_asset_manifest(topic_ids=topic_ids)
    return cast(list[dict[str, object]], manifest["assets"])


def _contains(text: str, term: str) -> bool:
    normalized = text.casefold()
    aliases = {
        "unit 2": ("unit 2", "alg1.2"),
        "unit 4": ("unit 4", "alg1.4"),
    }
    options = aliases.get(term.casefold(), (term.casefold(),))
    return any(option in normalized for option in options)


def evaluate_extracted_text(*, topic_id: int, asset_url: str, source_section: str, text: str) -> dict[str, object]:
    """Evaluate extracted text for required terms and basic extraction quality."""
    required_terms = _REQUIRED_TERMS_BY_TOPIC.get(topic_id, tuple(part for part in source_section.split() if len(part) > 2))
    missing_terms = [term for term in required_terms if not _contains(text, term)]
    problems: list[str] = []
    if len(text.strip()) < 80:
        problems.append("text_too_short")
    if missing_terms:
        problems.append("missing_required_terms")
    return {
        "topic_id": topic_id,
        "asset_url": asset_url,
        "source_section": source_section,
        "status": "pass" if not problems else "fail",
        "text_chars": len(text),
        "text_excerpt": text.strip()[:1200],
        "missing_terms": missing_terms,
        "problems": problems,
    }


def _fetch_bytes(url: str, tmp_dir: Path) -> Path:
    suffix = ".pdf" if url.lower().endswith(".pdf") else ".html"
    out = tmp_dir / (re.sub(r"[^a-zA-Z0-9]+", "-", url)[:120] + suffix)
    req = urllib.request.Request(url, headers={"User-Agent": "ai-tutor-exact-asset-probe/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        out.write_bytes(resp.read())
    return out


def _extract_text(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    raw = path.read_text(encoding="utf-8", errors="replace")
    raw = re.sub(r"<script\b.*?</script>", " ", raw, flags=re.I | re.S)
    raw = re.sub(r"<style\b.*?</style>", " ", raw, flags=re.I | re.S)
    raw = re.sub(r"<[^>]+>", " ", raw)
    return re.sub(r"\s+", " ", html.unescape(raw)).strip()


def run_fetch_probe(
    *,
    topic_ids: Sequence[int] | None = None,
    source_text_by_url: dict[str, str] | None = None,
) -> dict[str, object]:
    """Fetch exact selected assets into temp storage and evaluate extracted text."""
    rows: list[dict[str, object]] = []
    overrides = source_text_by_url or {}
    with tempfile.TemporaryDirectory(prefix="ai-tutor-algebra-assets-") as tmp:
        tmp_dir = Path(tmp)
        for asset in build_probe_plan(topic_ids=topic_ids):
            topic_id = int(cast(Any, asset["topic_id"]))
            url = str(asset["asset_url"])
            try:
                if url in overrides:
                    text = overrides[url]
                    extraction_source = "provided_text_override"
                else:
                    path = _fetch_bytes(url, tmp_dir)
                    text = _extract_text(path)
                    extraction_source = "temp_fetch"
                row = evaluate_extracted_text(
                    topic_id=topic_id,
                    asset_url=url,
                    source_section=str(asset["source_section"]),
                    text=text,
                )
                row["extraction_source"] = extraction_source
            except Exception as exc:  # pragma: no cover - network/extraction dependent
                row = {
                    "topic_id": topic_id,
                    "asset_url": url,
                    "source_section": str(asset["source_section"]),
                    "status": "fail",
                    "text_chars": 0,
                    "missing_terms": list(_REQUIRED_TERMS_BY_TOPIC.get(topic_id, ())),
                    "problems": [f"fetch_or_extract_error:{type(exc).__name__}"],
                }
            row.update({
                "source_key": asset["source_key"],
                "production_mutation": False,
                "db_import": False,
                "rag_chunk_creation": False,
            })
            rows.append(row)
    return {
        "mode": "temp_exact_asset_fetch_probe_only",
        "subject": "algebra",
        "production_mutation": False,
        "db_import": False,
        "rag_chunk_creation": False,
        "summary": summarize_probe_rows(rows),
        "rows": rows,
    }


def summarize_probe_rows(rows: Sequence[dict[str, object]]) -> dict[str, object]:
    source_counts = Counter(str(row.get("source_key")) for row in rows)
    pass_count = sum(1 for row in rows if row.get("status") == "pass")
    fail_count = sum(1 for row in rows if row.get("status") == "fail")
    return {
        "asset_count": len(rows),
        "pass_count": pass_count,
        "fail_count": fail_count,
        "source_counts": dict(sorted(source_counts.items())),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch/extract exact Algebra source assets into temp storage")
    parser.add_argument("--topic", action="append", type=int, default=[])
    parser.add_argument("--out", default="/tmp/ai-tutor-algebra-exact-asset-fetch-probe.json")
    parser.add_argument("--source-text-json", help="Optional JSON object mapping asset_url to already extracted text")
    args = parser.parse_args()
    source_text_by_url = None
    if args.source_text_json:
        payload = json.loads(Path(args.source_text_json).read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("--source-text-json must contain a JSON object")
        source_text_by_url = {str(key): str(value) for key, value in payload.items()}
    manifest = run_fetch_probe(topic_ids=args.topic or None, source_text_by_url=source_text_by_url)
    summary = cast(dict[str, object], manifest["summary"])
    fail_count = int(cast(Any, summary["fail_count"]))
    out = Path(args.out)
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": fail_count == 0, "out": str(out), **summary}, ensure_ascii=False))
    return 0 if fail_count == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
