from __future__ import annotations

from pathlib import Path


def test_collect_ops_metrics_reports_backup_age_and_disk(monkeypatch, tmp_path):
    from app import observability

    backup_dir = tmp_path / "backup_out"
    backup_dir.mkdir()
    manifest = backup_dir / "manifest-20260815T000000Z.md5"
    manifest.write_text("ok\n")
    monkeypatch.setattr(observability, "_probe_db", lambda: 1.0)
    monkeypatch.setattr(observability, "_probe_redis", lambda: 1.0)
    monkeypatch.setattr(observability, "_backup_out_path", lambda: backup_dir)

    metrics = observability.collect_ops_metrics()

    assert metrics["ai_tutor_db_up"] == 1.0
    assert metrics["ai_tutor_redis_up"] == 1.0
    assert metrics["ai_tutor_backup_latest_age_seconds"] >= 0.0
    assert 0.0 <= metrics["ai_tutor_upload_disk_used_percent"] <= 100.0


def test_ops_metrics_are_in_prometheus_payload(monkeypatch, tmp_path):
    from app import observability

    monkeypatch.setattr(
        observability,
        "collect_ops_metrics",
        lambda: {
            "ai_tutor_db_up": 1.0,
            "ai_tutor_redis_up": 1.0,
            "ai_tutor_upload_disk_used_percent": 12.5,
            "ai_tutor_backup_latest_age_seconds": 42.0,
        },
    )

    payload = observability.metrics_payload().decode("utf-8")

    assert "ai_tutor_db_up 1.0" in payload
    assert "ai_tutor_redis_up 1.0" in payload
    assert "ai_tutor_upload_disk_used_percent 12.5" in payload
    assert "ai_tutor_backup_latest_age_seconds 42.0" in payload
