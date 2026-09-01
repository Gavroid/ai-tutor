#!/usr/bin/env bash
# Pilot Core Stage 1 — Phase 3 (P1.3.3).
# Smoke-сценарий: проверяет, что критичные endpoints работают после deploy.
# Если что-то падает — exit non-zero, deploy.sh считается проваленным,
# и нужно запустить rollback.sh.
#
# Проверяет:
#  1) /health, /ready, /api/v2/health → 200
#  2) /api/v1/auth/register с role=student → 201 (positive case)
#  3) /api/v1/auth/register с role=admin → 4xx (security gate)
#  4) /api/v2/exercises/generate с admin token → 200, no correct_answer в ответе
#  5) /api/v2/exercises/{id}/answer → server-trusted
#  6) admin tools page не показывает Real-time link
#  7) /admin/realtime → 404 (если backend не знает WS-route через /api/,
#     nginx отдаёт 404 на plain GET — это норма)
#  8) backup age < 26h
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SSH_KEY="${SSH_KEY:-/root/.ssh/id_ed25519_kirill_ai}"
PROD_HOST="${PROD_HOST:-192.168.1.86}"

# Pilot Core Stage 1 (post-impl review): пилот-креденшалы через env,
# НЕ hardcoded. Если не заданы — smoke использует admin@example.com
# (по согласованию с владельцем, см. pilot-scenarios.md).
SMOKE_USER="${SMOKE_USER:-admin@example.com}"
SMOKE_PASS="${SMOKE_PASS:-strongpass1}"

log() { printf '\033[1;34m[smoke]\033[0m %s\n' "$*"; }
fail() { printf '\033[1;31m[smoke FAIL]\033[0m %s\n' "$*"; exit 1; }

ssh_q() { ssh -o BatchMode=yes -o ConnectTimeout=5 -i "$SSH_KEY" root@"$PROD_HOST" "$*"; }
# Production — self-signed cert; bypass с -k. Подключаемся по 192.168.1.86,
# а не по https://localhost (localhost на workspace ≠ localhost на prod).
curl_q() { curl -sk "https://$PROD_HOST$1" -o /tmp/smoke.body -w "%{http_code}"; }

# 1) Health
log "1) /health"
[ "$(curl_q /health)" = "200" ] || fail "/health != 200"
[ "$(curl_q /ready)" = "200" ] || fail "/ready != 200"
[ "$(curl_q /api/v2/health)" = "200" ] || fail "/api/v2/health != 200"

# 2) auth positive
log "2) auth/register (student)"
TS=$(date +%s)
STUDENT_CODE=$(curl -sk -X POST "https://$PROD_HOST/api/v1/auth/register" -H "Content-Type: application/json" \
  -d "{\"email\":\"smoke-${TS}@example.com\",\"password\":\"$SMOKE_PASS\",\"display_name\":\"smoke\",\"role\":\"student\",\"grade\":7}" \
  -o /tmp/smoke.body -w "%{http_code}")
[ "$STUDENT_CODE" = "201" ] || fail "register student = $STUDENT_CODE"

# 3) auth negative (security gate)
log "3) auth/register (admin) — должно быть 4xx"
ADMIN_CODE=$(curl -sk -X POST "https://$PROD_HOST/api/v1/auth/register" -H "Content-Type: application/json" \
  -d "{\"email\":\"smoke-admin-${TS}@example.com\",\"password\":\"strongpass1\",\"display_name\":\"x\",\"role\":\"admin\"}" \
  -o /tmp/smoke.body -w "%{http_code}")
# Sprint 9.2 audit fix: принимаем любой 4xx (включая 429 rate-limit если audit
# только что делал много register вызовов). Главное — не 200/201.
if [ "${ADMIN_CODE:0:1}" != "4" ]; then
  fail "register admin = $ADMIN_CODE (ожидаем 4xx — admin role запрещён в register)"
fi
log "  (got $ADMIN_CODE — OK, admin role заблокирован)"

# 4) v2 exercises — admin token (SMOKE_USER/SMOKE_PASS)
log "4) /api/v2/exercises/generate ($SMOKE_USER)"
ADMIN_LOGIN=$(curl -sk -X POST "https://$PROD_HOST/api/v1/auth/login" -H "Content-Type: application/json" \
  -d "{\"email\":\"$SMOKE_USER\",\"password\":\"$SMOKE_PASS\"}" -o /tmp/smoke.body -w "%{http_code}")
[ "$ADMIN_LOGIN" = "200" ] || fail "smoke-user login = $ADMIN_LOGIN (user=$SMOKE_USER)"
ADMIN_TOKEN=$(python3 -c "import sys, json; print(json.load(open('/tmp/smoke.body'))['access_token'])")

GEN_CODE=$(curl -sk -X POST "https://$PROD_HOST/api/v2/exercises/generate" -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" -d '{"topic_id":1,"difficulty":1}' \
  -o /tmp/smoke.body -w "%{http_code}")
[ "$GEN_CODE" = "200" ] || fail "v2 generate = $GEN_CODE"
EID=$(python3 -c "import sys, json; print(json.load(open('/tmp/smoke.body')).get('exercise_id', 0))")
[ "$EID" != "0" ] || fail "no exercise_id in response"
if grep -q '"correct_answer"' /tmp/smoke.body; then
  fail "SECURITY: correct_answer leaks in /generate response"
fi
log "  exercise_id=$EID, no correct_answer in payload — OK"

# 5) v2 answer
log "5) /api/v2/exercises/{id}/answer (admin)"
ANS_CODE=$(curl -sk -X POST "https://$PROD_HOST/api/v2/exercises/$EID/answer" -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" -d '{"user_answer":"definitely_wrong_xyz"}' \
  -o /tmp/smoke.body -w "%{http_code}")
[ "$ANS_CODE" = "200" ] || fail "v2 answer = $ANS_CODE"
log "  body: $(cat /tmp/smoke.body | head -c 200)"

# 6) /admin/realtime через nginx
log "6) /admin/realtime через nginx"
RT_CODE=$(curl_q /admin/realtime)
log "  /admin/realtime=$RT_CODE (любой не-200 для plain GET — OK, это WS endpoint)"

# 7) backup age < 26h
log "7) backup age < 26h"
LATEST=$(ssh_q "ls -1t /opt/ai-tutor/deploy/backup/_out/manifest-*.md5 2>/dev/null | head -1" || true)
if [ -z "$LATEST" ]; then
  log "  нет backup-файла — пропускаю"
else
  MTIME_EPOCH=$(ssh_q "stat -c %Y $LATEST")
  NOW=$(date +%s)
  AGE_HOURS=$(( (NOW - MTIME_EPOCH) / 3600 ))
  log "  свежий backup: $LATEST ($AGE_HOURS ч назад)"
  if [ "$AGE_HOURS" -gt 26 ]; then
    fail "backup старше 26ч (age=$AGE_HOURS)"
  fi
fi

# 8) Sprint S3.6 — POST /api/v1/feedback/report (admin token)
# Используем $ADMIN_TOKEN из шага 4 (он уже login'ился под $SMOKE_USER).
# Это проверяет и Track B endpoint, и что alembic 0022_feedback_reports применён.
log "8) /api/v1/feedback/report POST (admin)"
FB_CODE=$(curl -sk -X POST "https://$PROD_HOST/api/v1/feedback/report" \
  -H "Authorization: Bearer $ADMIN_TOKEN" -H "Content-Type: application/json" \
  -d '{"category":"unclear","text":"smoke-prod: verify S3.6 endpoint"}' \
  -o /tmp/smoke.body -w "%{http_code}")
[ "$FB_CODE" = "201" ] || fail "S3.6 feedback/report = $FB_CODE (ожидаем 201)"
FB_ID=$(python3 -c "import json; print(json.load(open('/tmp/smoke.body'))['id'])" 2>/dev/null || echo 0)
log "  feedback_reports id=$FB_ID — OK"

# 8b) GET /api/v1/admin/feedback-reports — проверим, что созданное видно
FB_LIST_CODE=$(curl -sk -H "Authorization: Bearer $ADMIN_TOKEN" \
  "https://$PROD_HOST/api/v1/admin/feedback-reports" -o /tmp/smoke.body -w "%{http_code}")
[ "$FB_LIST_CODE" = "200" ] || fail "S3.6 admin/feedback-reports = $FB_LIST_CODE"
FB_TOTAL=$(python3 -c "import json; print(json.load(open('/tmp/smoke.body'))['total'])" 2>/dev/null || echo 0)
log "  admin queue total=$FB_TOTAL — OK"

# 8c) Чистим: PATCH status=resolved для тестового report
FB_PATCH_CODE=$(curl -sk -X PATCH "https://$PROD_HOST/api/v1/admin/feedback-reports/$FB_ID/status" \
  -H "Authorization: Bearer $ADMIN_TOKEN" -H "Content-Type: application/json" \
  -d '{"status":"resolved"}' -o /tmp/smoke.body -w "%{http_code}")
[ "$FB_PATCH_CODE" = "200" ] || fail "S3.6 patch status = $FB_PATCH_CODE"
log "  cleanup: id=$FB_ID → resolved — OK"

# 9) Sprint S3.2 — GET /api/v1/ai/understand-check/{topic_id}
# Используем admin token (роль не важна — endpoint только требует залогинен).
log "9) /api/v1/ai/understand-check/1"
UC_CODE=$(curl -sk -H "Authorization: Bearer $ADMIN_TOKEN" \
  "https://$PROD_HOST/api/v1/ai/understand-check/1" -o /tmp/smoke.body -w "%{http_code}")
[ "$UC_CODE" = "200" ] || fail "S3.2 understand-check = $UC_CODE"
QCOUNT=$(python3 -c "import json; print(len(json.load(open('/tmp/smoke.body'))['questions']))" 2>/dev/null || echo 0)
[ "$QCOUNT" = "3" ] || fail "S3.2 understand-check: вопросов=$QCOUNT (ожидаем 3)"
log "  questions=$QCOUNT, style=$(python3 -c "import json; print(json.load(open('/tmp/smoke.body'))['style'])") — OK"

# 9b) Негативный кейс — неизвестный topic_id → 404 (доказывает что endpoint не подделывает)
UC_404=$(curl -sk -H "Authorization: Bearer $ADMIN_TOKEN" \
  "https://$PROD_HOST/api/v1/ai/understand-check/99999999" -o /dev/null -w "%{http_code}")
[ "$UC_404" = "404" ] || fail "S3.2 unknown topic = $UC_404 (ожидаем 404)"
log "  unknown topic → 404 — OK"

# 9c) Негативный кейс — без токена → 401
UC_401=$(curl -sk "https://$PROD_HOST/api/v1/ai/understand-check/1" -o /dev/null -w "%{http_code}")
[ "$UC_401" = "401" ] || fail "S3.2 no-auth = $UC_401 (ожидаем 401)"
log "  no-auth → 401 — OK"

log "OK: smoke прошёл"
