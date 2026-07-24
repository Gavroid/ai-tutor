# Grafana Dashboards — Sprint 39

Дашборды для AI-репетитора: parent-friendly и system overview.

## 📊 Доступные дашборды

### 1. `ai-tutor-overview.json` (Sprint 9.2)
System overview:
- HTTP requests/min
- AI tokens/min
- AI requests by mode

### 2. `parent-dashboard.json` (Sprint 39, NEW)
**T1D-friendly view для parent'а** — мониторинг Кирилла:
- 🟢 **Streak** (current/longest) — T1D-friendly, не показывает "STREAK LOST"
- 📊 **Активность** (attempts/day) за 7 дней
- 🎯 **Mastery по предметам** (gauge) — зеленый ≥70%, желтый ≥40%
- ⚠️ **Слабые темы** (mastery < 0.6) — table с actionable list
- 🛑 **T1D Session Pauses** по reason (break/hypo/hyper/other) — piechart
- ⏱ **Средняя длина сессии** — T1D safety (>40 мин = red)
- 📈 **Weekly trend** — this week vs prev week

### 3. `system-overview.json` (Sprint 39, NEW)
Production health:
- 🚨 5xx ошибки (rate/min) — если >0, alert
- ⏱ Latency p95 (seconds)
- 👥 Active users (last 5m)
- 🤖 AI requests (req/min)
- 📊 HTTP requests by status
- 📚 Materials по status (draft/ai_generated/approved/published)
- ⚡ Workers (uvicorn)
- 🛑 Telegram alerts (5xx → TG)

## 🔧 Custom metrics (TODO: expose в Prometheus)

`parent_*` метрики в `parent-dashboard.json` пока **не существуют** в Prometheus.
Чтобы дашборд показывал реальные данные, нужно:

### Sprint 39 follow-up: expose parent metrics

В `apps/backend/app/parents/router.py::child_dashboard` добавить Prometheus counters:
```python
from prometheus_client import Counter, Gauge, Histogram

# Counter — attempts by day
parent_attempts_total = Counter(
    "parent_attempts_total",
    "Total attempts by student (parent view)",
    ["user_id", "day"]
)

# Gauge — streak
parent_streak_current_streak_days = Gauge(
    "parent_streak_current_streak_days",
    "Current streak (T1D-friendly)",
    ["user_id"]
)
parent_streak_longest_streak_days = Gauge(
    "parent_streak_longest_streak_days",
    "Longest streak",
    ["user_id"]
)

# Gauge — mastery by subject
parent_subject_mastery_avg = Gauge(
    "parent_subject_mastery_avg",
    "Average mastery by subject",
    ["user_id", "subject"]
)

# Gauge — session pause reason
parent_session_pauses_total = Counter(
    "parent_session_pauses_total",
    "T1D session pauses (Sprint 34)",
    ["user_id", "reason"]
)

# Histogram — session duration
parent_session_duration_seconds = Histogram(
    "parent_session_duration_seconds",
    "Session duration (T1D safety)"
)
```

Эти метрики будут в `/metrics` endpoint и Grafana сможет их собирать.

## 🚀 Setup

Dashboards **автоматически** импортируются через Grafana provisioning:
```yaml
# deploy/grafana/provisioning/dashboards/dashboards.yml
providers:
  - name: 'AI Tutor'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /etc/grafana/dashboards
```

Доступ к Grafana: `https://192.168.1.86/grafana` (admin/admin или internal).

## 📝 Security note

`parent-dashboard.json` НЕ содержит PHI (glucose data, CGM). Только timing-based метрики
(Sprint 34 T1D safety). CGM integration — Sprint 40.
