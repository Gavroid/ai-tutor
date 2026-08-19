from __future__ import annotations

from scripts.algebra_asset_extraction_snippets import build_snippet_manifest, validate_snippet_manifest


def test_snippet_manifest_covers_all_exact_assets_with_local_snippets() -> None:
    manifest = build_snippet_manifest()

    assert manifest["mode"] == "local_asset_snippet_manifest_only"
    assert manifest["topic_count"] == 19
    assert len(manifest["snippets"]) == 19
    assert len({row["topic_id"] for row in manifest["snippets"]}) == 19
    assert all(row["snippet"] for row in manifest["snippets"])
    assert all(row["production_mutation"] is False for row in manifest["snippets"])


def test_snippet_manifest_validation_passes_current_manifest() -> None:
    assert validate_snippet_manifest(build_snippet_manifest()) == {"ok": True, "snippet_count": 19, "problems": []}


def test_snippet_manifest_validation_rejects_empty_or_unmapped_snippet() -> None:
    manifest = build_snippet_manifest()
    bad = dict(manifest)
    snippets = [dict(row) for row in manifest["snippets"]]
    snippets[0]["snippet"] = ""
    bad["snippets"] = snippets

    result = validate_snippet_manifest(bad)

    assert result["ok"] is False
    assert "empty_snippet" in result["problems"]
