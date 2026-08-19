from __future__ import annotations

from scripts.algebra_source_asset_manifest import build_asset_manifest, validate_asset_manifest


def test_asset_manifest_covers_all_algebra_topics_with_exact_assets() -> None:
    manifest = build_asset_manifest()

    assert manifest["mode"] == "exact_source_asset_manifest_only"
    assert manifest["topic_count"] == 19
    assert len(manifest["assets"]) == 19
    assert len({asset["topic_id"] for asset in manifest["assets"]}) == 19
    assert all(asset["asset_url"].startswith(("https://im.kendallhunt.com/", "http://www.wallace.ccfaculty.org/")) for asset in manifest["assets"])
    assert all(asset["production_mutation"] is False for asset in manifest["assets"])


def test_asset_manifest_validation_rejects_missing_or_unsafe_asset_url() -> None:
    manifest = build_asset_manifest()
    bad = dict(manifest)
    assets = [dict(asset) for asset in manifest["assets"]]
    assets[0]["asset_url"] = "https://example.com/random.pdf"
    bad["assets"] = assets

    result = validate_asset_manifest(bad)

    assert result["ok"] is False
    assert "unapproved_asset_url" in result["problems"]


def test_asset_manifest_validation_passes_current_manifest() -> None:
    result = validate_asset_manifest(build_asset_manifest())

    assert result == {"ok": True, "asset_count": 19, "problems": []}
