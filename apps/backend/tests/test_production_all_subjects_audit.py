from __future__ import annotations

from scripts.production_all_subjects_audit import audit_subjects_payload


def test_audit_subjects_payload_requires_all_subjects_ready() -> None:
    payload = [
        {
            "code": "math",
            "mvp_status": "mvp_ready",
            "route_ready": True,
            "rag_ready": True,
            "practice_ready": True,
            "topic_count": 2,
            "route_topic_count": 2,
            "source_topic_count": 2,
            "practice_topic_count": 2,
        },
        {
            "code": "rus",
            "mvp_status": "preview",
            "route_ready": True,
            "rag_ready": True,
            "practice_ready": True,
            "topic_count": 1,
            "route_topic_count": 1,
            "source_topic_count": 1,
            "practice_topic_count": 1,
        },
    ]

    result = audit_subjects_payload(payload, expected_subject_count=2)

    assert result["ok"] is False
    assert "rus:not_mvp_ready" in result["problems"]


def test_audit_subjects_payload_passes_complete_ready_payload() -> None:
    payload = [
        {
            "code": "math",
            "mvp_status": "mvp_ready",
            "route_ready": True,
            "rag_ready": True,
            "practice_ready": True,
            "topic_count": 2,
            "route_topic_count": 2,
            "source_topic_count": 2,
            "practice_topic_count": 2,
        },
        {
            "code": "rus",
            "mvp_status": "mvp_ready",
            "route_ready": True,
            "rag_ready": True,
            "practice_ready": True,
            "topic_count": 1,
            "route_topic_count": 1,
            "source_topic_count": 1,
            "practice_topic_count": 1,
        },
    ]

    result = audit_subjects_payload(payload, expected_subject_count=2)

    assert result["ok"] is True
    assert result["problems"] == []
    assert result["subject_count"] == 2
    assert result["total_topics"] == 3
