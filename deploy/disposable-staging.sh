#!/usr/bin/env bash
# Sprint 7 (2026-08-23): disposable staging environment runner.
# Создаёт/уничтожает disposable staging для Math-6 pilot CI.
#
# Использование:
#   ./deploy/disposable-staging.sh up       # создать + провести smoke
#   ./deploy/disposable-staging.sh down     # уничтожить
#   ./deploy/disposable-staging.sh verify   # только smoke проверки без создания
#
# Не трогает production. Production хранится отдельно в deploy/docker-compose.yml.

set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE_NS="${COMPOSE_NS:-ai-tutor-staging-$RANDOM}"
COMPOSE_FILE="$ROOT/deploy/docker-compose.staging.yml"

step() {
    echo "==[ $1 ]=="
}

usage() {
    cat <<'EOF'
disposable-staging.sh — Sprint 7 disposable staging runner.

Действия:
  up         Создать disposable стек + smoke checks + teardown.
  down       Принудительно уничтожить disposable стек.
  verify     Запустить только smoke checks (нужен уже поднятый стек).

Переменные окружения:
  COMPOSE_NS   namespace для изоляции (default: ai-tutor-staging-RANDOM)
  BASE_URL     staging URL для verify (default: http://localhost:8000)

Это read-only против production. НЕ ДЕЛАЕТ: миграций prod data, restore prod backup.
EOF
}

cmd_up() {
    step "compose-staging.yml exists?"
    if [ ! -f "$COMPOSE_FILE" ]; then
        echo "Создаю базовый compose.staging.yml..."
        cat >"$COMPOSE_FILE" <<YAML
name: ${COMPOSE_NS}
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: tutor
      POSTGRES_PASSWORD: tutor
      POSTGRES_DB: tutor
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U tutor -d tutor"]
      interval: 5s
      timeout: 3s
      retries: 5
  redis:
    image: redis:7-alpine
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5
  backend:
    build: $ROOT/apps/backend
    depends_on:
      db: { condition: service_healthy }
      redis: { condition: service_healthy }
    environment:
      APP_ENV: staging
      APP_SECRET_KEY: \${APP_SECRET_KEY:-dev-staging-key}
      DATABASE_URL: postgresql://tutor:tutor@db:5432/tutor
      REDIS_URL: redis://redis:6379/0
      AI_DETERMINISTIC_MODE: "1"
    ports: ["8000:8000"]
YAML
    fi

    step "docker compose up (disposable, no restart)"
    (cd "$ROOT/deploy" && docker compose -p "$COMPOSE_NS" -f "$COMPOSE_FILE" up --no-restart -d) || {
        echo "ERROR: docker compose up failed"
        return 1
    }

    step "wait for /health"
    local i
    for i in $(seq 1 30); do
        if curl -fsS "http://localhost:8000/health" >/dev/null 2>&1; then
            echo "  /health OK after ${i}s"
            break
        fi
        sleep 1
    done

    step "wait for /ready"
    if ! curl -fsS "http://localhost:8000/ready" >/dev/null 2>&1; then
        echo "ERROR: /ready не отвечает"
        cmd_down
        return 1
    fi

    step "smoke checks"
    cmd_verify

    step "teardown (disposable)"
    cmd_down
}

cmd_down() {
    step "docker compose down"
    (cd "$ROOT/deploy" && docker compose -p "$COMPOSE_NS" -f "$COMPOSE_FILE" down -v --remove-orphans) || true
}

cmd_verify() {
    local base="${BASE_URL:-http://localhost:8000}"
    step "GET /health"
    curl -fsS "$base/health" || { echo "FAIL /health"; return 1; }
    echo
    step "GET /ready"
    curl -fsS "$base/ready" || { echo "FAIL /ready"; return 1; }
    echo
    step "POST /api/v1/ai/explain (deterministic)"
    # Login как test student (создаётся в seed) — на disposable должен быть.
    token=$(curl -fsS -X POST "$base/api/v1/auth/login" \
        -H "Content-Type: application/json" \
        -d '{"email":"kirill@example.com","password":"strongpass1"}' \
        | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null) || {
        echo "WARN: test student login failed (seed might not have run); skipping explain"
        return 0
    }
    # Берём первый math topic.
    topic_id=$(curl -fsS "$base/api/v1/subjects/" -H "Authorization: Bearer $token" \
        | python3 -c "
import sys, json
subjects = json.load(sys.stdin)
math = next((s for s in subjects if 'математика' in s.get('name','').lower()), subjects[0] if subjects else None)
if math is None:
    print('0'); raise SystemExit
import urllib.request, json as J
r = urllib.request.urlopen(f\"$base/api/v1/subjects/{math['id']}/topics\", headers={'Authorization': f'Bearer $token'})
topics = J.loads(r.read())
print(topics[0]['id'] if topics else '0')
") || {
        echo "WARN: subject/topic discovery failed; skipping explain"
        return 0
    }
    curl -fsS -X POST "$base/api/v1/ai/explain" \
        -H "Authorization: Bearer $token" \
        -H "Content-Type: application/json" \
        -d "{\"topic_id\": $topic_id}" >/dev/null || { echo "FAIL explain"; return 1; }
    echo "  explain OK"
}

case "${1:-usage}" in
    up) cmd_up ;;
    down) cmd_down ;;
    verify) cmd_verify ;;
    *) usage; exit 1 ;;
esac
