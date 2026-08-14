# Grafana Dashboards — AI-Tutor

Provisioned dashboards for the current pilot deployment.

## Available Dashboards

### `ai-tutor-overview.json`

System overview based on real Prometheus metrics currently exposed by backend:

- HTTP request rate by route/status.
- HTTP 5xx rate.
- AI token rate by role.
- AI request rate by mode/status.
- Latency p95 from `http_request_duration_seconds`.

### `system-overview.json`

Production-health oriented panels. Keep panels tied only to metrics that exist in `/metrics`.

### `parent-dashboard.json`

Historical parent-oriented dashboard. Treat as optional/legacy unless the referenced `parent_*` metrics are exposed.
The application parent dashboard is the source of truth for parent-facing progress summaries.

## Alerts

Alert rules are provisioned separately under:

```text
deploy/grafana/provisioning/alerting/ai-tutor-alerts.yml
deploy/prometheus/alerts.yml
```

Current alert scope:

- backend scrape target down;
- backend HTTP 5xx;
- unexpected 4xx spikes, excluding expected draft 404 and unauthenticated snapshot probes;
- login 429 spikes;
- readiness failures;
- disk usage high when node filesystem metrics are available.

## Maintenance Rules

- Do not add panels for metrics that do not exist in `/metrics`.
- Do not add Telegram/email delivery in this phase.
- Prefer application dashboards for parent/teacher/student product views; Grafana is for ops.
- After provisioning changes: restart Grafana/Prometheus and verify rules/dashboards load.
