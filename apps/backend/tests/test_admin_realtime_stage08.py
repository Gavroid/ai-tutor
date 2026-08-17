from __future__ import annotations


def test_admin_realtime_system_health_uses_app_level_ops_probes(monkeypatch):
    from app.admin import realtime

    monkeypatch.setattr(
        realtime,
        "collect_ops_metrics",
        lambda: {
            "ai_tutor_db_up": 1.0,
            "ai_tutor_redis_up": 1.0,
            "ai_tutor_upload_disk_used_percent": 46.7,
            "ai_tutor_backup_latest_age_seconds": 3600.0,
        },
    )

    result = realtime._system_health()

    assert result["backend"] == "ok"
    assert result["db"] == "ok"
    assert result["redis"] == "ok"
    assert result["upload_disk_used_percent"] == 46.7
    assert result["backup_latest_age_seconds"] == 3600.0


def test_admin_realtime_system_health_marks_failed_ops_probes_down(monkeypatch):
    from app.admin import realtime

    monkeypatch.setattr(
        realtime,
        "collect_ops_metrics",
        lambda: {
            "ai_tutor_db_up": 0.0,
            "ai_tutor_redis_up": 0.0,
            "ai_tutor_upload_disk_used_percent": 91.2,
            "ai_tutor_backup_latest_age_seconds": -1.0,
        },
    )

    result = realtime._system_health()

    assert result["backend"] == "ok"
    assert result["db"] == "down"
    assert result["redis"] == "down"
    assert result["upload_disk_used_percent"] == 91.2
    assert result["backup_latest_age_seconds"] == -1.0
