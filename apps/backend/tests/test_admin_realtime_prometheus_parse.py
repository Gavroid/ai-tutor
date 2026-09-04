from app.admin.realtime import parse_prometheus_snapshot


def test_parse_prometheus_snapshot_aggregates_workers():
    text = """
# HELP ai_tokens_total Total AI tokens consumed
# TYPE ai_tokens_total counter
ai_tokens_total{role="input"} 100.0
ai_tokens_total{role="output"} 40.0
# HELP ai_requests_total Total AI requests
# TYPE ai_requests_total counter
ai_requests_total{mode="explain",status="ok"} 2.0
ai_requests_total{mode="explain",status="error"} 1.0
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="GET",path="/api/v1/student/topics/{topic_id}/draft",status="404"} 4.0
http_requests_total{method="GET",path="/api/v1/admin/realtime/snapshot",status="401"} 1.0
http_requests_total{method="GET",path="/api/v1/ai/explain",status="500"} 2.0
http_requests_total{method="GET",path="/api/v1/auth/me",status="200"} 10.0
"""

    parsed = parse_prometheus_snapshot(text)

    assert parsed["ai_tokens"] == {"input": 100, "output": 40}
    assert parsed["ai_modes"] == {"explain": {"ok": 2, "error": 1}}
    assert parsed["http_total"] == {"2xx": 10, "4xx": 5, "5xx": 2}
    expected = [item for item in parsed["http_breakdown"] if item["kind"] == "expected"]
    actionable = [item for item in parsed["http_breakdown"] if item["kind"] == "actionable"]
    assert len(expected) == 2
    assert len(actionable) == 1
    assert actionable[0]["status"] == "500"
