from app.admin.realtime import classify_http_status_sample


def test_classify_expected_missing_draft_404():
    result = classify_http_status_sample("/api/v1/student/topics/{topic_id}/draft", "404", 4)

    assert result["bucket"] == "4xx"
    assert result["kind"] == "expected"
    assert result["reason"] == "missing_topic_draft"


def test_classify_actionable_unknown_404():
    result = classify_http_status_sample("/api/v1/unknown", "404", 2)

    assert result["bucket"] == "4xx"
    assert result["kind"] == "actionable"
    assert result["reason"] == "unexpected_4xx"


def test_classify_actionable_5xx():
    result = classify_http_status_sample("/api/v1/ai/explain", "500", 1)

    assert result["bucket"] == "5xx"
    assert result["kind"] == "actionable"
    assert result["reason"] == "server_error"
