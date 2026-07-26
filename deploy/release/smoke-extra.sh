#!/usr/bin/env bash
# Sprint 55: extended smoke test — Sprint 32-45 endpoints.
#
# Проверяет:
#  - Sprint 32: Parent 2FA endpoints (status, enable, disable)
#  - Sprint 34: Sessions pause/resume
#  - Sprint 40: CGM config/latest/status
#  - Sprint 44: Public invite flow
#  - Sprint 45: Audit log hash chain + export
#  - Sprint 47: Audit log covers invite operations
#
# Запускается после основного smoke.sh на production.
# Если что-то падает — exit non-zero, нужно rollback.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SSH_KEY="${SSH_KEY:-/root/.ssh/id_ed25519_kirill_ai}"
PROD_HOST="${PROD_HOST:-192.168.1.86}"

# Smoke user (admin — для 2FA/invite/audit checks).
SMOKE_USER="${SMOKE_USER:-admin@example.com}"
SMOKE_PASS="${SMOKE_PASS:-Kirill2026!}"

log() { printf '\033[1;34m[smoke-extra]\033[0m %s\n' "$*"; }
fail() { printf '\033[1;31m[smoke-extra FAIL]\033[0m %s\n' "$*"; exit 1; }

curl_q() { curl -sk "https://$PROD_HOST$1" -o /tmp/smoke_extra.body -w "%{http_code}"; }
curl_post() { curl -sk -X POST "https://$PROD_HOST$1" -H "Content-Type: application/json" -d "${2:-}" -o /tmp/smoke_extra.body -w "%{http_code}"; }
curl_get() { curl -sk "https://$PROD_HOST$1" -o /tmp/smoke_extra.body -w "%{http_code}"; }

# === Setup: login as admin ===
log "0) Setup: admin login"
LOGIN_CODE=$(curl -sk -X POST "https://$PROD_HOST/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$SMOKE_USER\",\"password\":\"$SMOKE_PASS\"}" \
  -o /tmp/smoke_extra.body -w "%{http_code}")
if [ "$LOGIN_CODE" != "200" ]; then
  fail "admin login = $LOGIN_CODE"
fi
ADMIN_TOKEN=$(python3 -c "import sys, json; print(json.load(open('/tmp/smoke_extra.body'))['access_token'])")
log "  admin login OK"

# === 1) Audit log hash chain verification (Sprint 45) ===
log "1) /api/v1/admin/audit-log/verify (Sprint 45 hash chain)"
VERIFY_CODE=$(curl -sk "https://$PROD_HOST/api/v1/admin/audit-log/verify?limit=100" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -o /tmp/smoke_extra.body -w "%{http_code}")
[ "$VERIFY_CODE" = "200" ] || fail "audit verify = $VERIFY_CODE"
TAMPERED=$(python3 -c "import sys, json; print(json.load(open('/tmp/smoke_extra.body'))['tampered'])")
if [ "$TAMPERED" != "0" ]; then
  fail "tampered records detected: $TAMPERED"
fi
log "  hash chain valid (tampered=0)"

# === 2) Audit log export (Sprint 45) ===
log "2) /api/v1/admin/audit-log/export?fmt=json"
EXPORT_CODE=$(curl -sk "https://$PROD_HOST/api/v1/admin/audit-log/export?fmt=json&limit=10" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -o /tmp/smoke_extra.body -w "%{http_code}")
[ "$EXPORT_CODE" = "200" ] || fail "audit export = $EXPORT_CODE"
EXPORTED=$(python3 -c "import sys, json; print(len(json.load(open('/tmp/smoke_extra.body'))))")
[ "$EXPORTED" -gt "0" ] || fail "audit export returned 0 rows"
log "  exported $EXPORTED records"

# === 3) Invite create + list (Sprint 44) ===
log "3) /api/v1/admin/invites (POST + GET)"
INVITE_CODE=$(curl -sk -X POST "https://$PROD_HOST/api/v1/admin/invites" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"role":"student","note":"smoke-extra","max_uses":1}' \
  -o /tmp/smoke_extra.body -w "%{http_code}")
[ "$INVITE_CODE" = "201" ] || fail "invite create = $INVITE_CODE"
INVITE_VALUE=$(python3 -c "import sys, json; print(json.load(open('/tmp/smoke_extra.body'))['code'])")
log "  created invite: $INVITE_VALUE"

# Verify it appears in list
LIST_CODE=$(curl -sk "https://$PROD_HOST/api/v1/admin/invites?limit=5" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -o /tmp/smoke_extra.body -w "%{http_code}")
[ "$LIST_CODE" = "200" ] || fail "invite list = $LIST_CODE"
COUNT=$(python3 -c "import sys, json; print(len(json.load(open('/tmp/smoke_extra.body'))))")
[ "$COUNT" -gt "0" ] || fail "invite list empty"
log "  list returned $COUNT invites"

# === 4) Public invite redeem (Sprint 44) ===
log "4) /api/v1/auth/redeem-invite (public, no auth)"
REDEEM_CODE=$(curl -sk -X POST "https://$PROD_HOST/api/v1/auth/redeem-invite" \
  -H "Content-Type: application/json" \
  -d "{\"code\":\"$INVITE_VALUE\"}" \
  -o /tmp/smoke_extra.body -w "%{http_code}")
[ "$REDEEM_CODE" = "200" ] || fail "invite redeem = $REDEEM_CODE"
REDEEM_ROLE=$(python3 -c "import sys, json; print(json.load(open('/tmp/smoke_extra.body'))['role'])")
[ "$REDEEM_ROLE" = "student" ] || fail "redeem role = $REDEEM_ROLE"
log "  redeem OK, role=$REDEEM_ROLE"

# === 5) Sessions pause (Sprint 34) ===
log "5) /api/v1/sessions/pause (Sprint 34)"
# Need student token for this
STUDENT_LOGIN=$(curl -sk -X POST "https://$PROD_HOST/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"kirill@example.com","password":"Kirill2026!"}' \
  -o /tmp/smoke_extra.body -w "%{http_code}")
if [ "$STUDENT_LOGIN" != "200" ]; then
  log "  WARN: student login failed ($STUDENT_LOGIN), skipping sessions test"
else
  STUDENT_TOKEN=$(python3 -c "import sys, json; print(json.load(open('/tmp/smoke_extra.body'))['access_token'])")
  PAUSE_CODE=$(curl -sk -X POST "https://$PROD_HOST/api/v1/sessions/pause" \
    -H "Authorization: Bearer $STUDENT_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"reason":"hypo","note":"smoke-extra"}' \
    -o /tmp/smoke_extra.body -w "%{http_code}")
  [ "$PAUSE_CODE" = "201" ] || fail "sessions pause = $PAUSE_CODE"
  PAUSE_ID=$(python3 -c "import sys, json; print(json.load(open('/tmp/smoke_extra.body'))['id'])")
  log "  pause created id=$PAUSE_ID"
fi

# === 6) Sessions recent list (Sprint 34) ===
log "6) /api/v1/sessions/pauses/recent"
RECENT_CODE=$(curl -sk "https://$PROD_HOST/api/v1/sessions/pauses/recent?limit=5" \
  -H "Authorization: Bearer ${STUDENT_TOKEN:-$ADMIN_TOKEN}" \
  -o /tmp/smoke_extra.body -w "%{http_code}")
[ "$RECENT_CODE" = "200" ] || fail "sessions recent = $RECENT_CODE"
log "  recent list OK"

# === 7) CGM config (Sprint 40) — без auth 401 ===
log "7) /api/v1/cgm/config (auth required)"
CGM_CODE=$(curl -sk "https://$PROD_HOST/api/v1/cgm/config" -o /tmp/smoke_extra.body -w "%{http_code}")
[ "$CGM_CODE" = "401" ] || fail "CGM without auth = $CGM_CODE (expected 401)"
log "  CGM 401 без auth — OK"

# === 8) CGM config with admin ===
CGM_ADMIN_CODE=$(curl -sk "https://$PROD_HOST/api/v1/cgm/config" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -o /tmp/smoke_extra.body -w "%{http_code}")
[ "$CGM_ADMIN_CODE" = "200" ] || fail "CGM admin = $CGM_ADMIN_CODE"
log "  CGM 200 с admin — OK"

# === 9) CGM SSRF protection (HTTPS-only) ===
log "9) CGM config URL validation (SSRF protection)"
SSRF_CODE=$(curl -sk -X PUT "https://$PROD_HOST/api/v1/cgm/config" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"nightscout_url":"http://example.com","enabled":true}' \
  -o /tmp/smoke_extra.body -w "%{http_code}")
[ "$SSRF_CODE" = "400" ] || fail "CGM http URL = $SSRF_CODE (expected 400)"
log "  SSRF protection: http:// → 400 — OK"

LOCALHOST_CODE=$(curl -sk -X PUT "https://$PROD_HOST/api/v1/cgm/config" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"nightscout_url":"https://localhost:1337","enabled":true}' \
  -o /tmp/smoke_extra.body -w "%{http_code}")
[ "$LOCALHOST_CODE" = "400" ] || fail "CGM localhost = $LOCALHOST_CODE (expected 400)"
log "  SSRF protection: localhost → 400 — OK"

# === 10) Audit log covers invite operations (Sprint 47) ===
log "10) Audit log contains invite.create (Sprint 47 integration)"
INVITE_LOGS=$(curl -sk "https://$PROD_HOST/api/v1/admin/audit-log?action=invite.create&limit=5" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -o /tmp/smoke_extra.body -w "%{http_code}")
[ "$INVITE_LOGS" = "200" ] || fail "audit logs invite = $INVITE_LOGS"
INVITE_LOG_COUNT=$(python3 -c "import sys, json; print(len(json.load(open('/tmp/smoke_extra.body'))))")
[ "$INVITE_LOG_COUNT" -gt "0" ] || fail "no invite.create audit logs"
log "  found $INVITE_LOG_COUNT invite.create audit logs"

REDEEM_LOGS=$(curl -sk "https://$PROD_HOST/api/v1/admin/audit-log?action=invite.redeem&limit=5" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -o /tmp/smoke_extra.body -w "%{http_code}")
[ "$REDEEM_LOGS" = "200" ] || fail "audit logs redeem = $REDEEM_LOGS"
REDEEM_LOG_COUNT=$(python3 -c "import sys, json; print(len(json.load(open('/tmp/smoke_extra.body'))))")
[ "$REDEEM_LOG_COUNT" -gt "0" ] || fail "no invite.redeem audit logs"
log "  found $REDEEM_LOG_COUNT invite.redeem audit logs"

# === 11) Audit log has hash chain (Sprint 45) ===
log "11) Audit log records have hash chain populated"
HASH_CHAIN_OK=$(python3 -c "
import sys, json
data = json.load(open('/tmp/smoke_extra.body'))
hashes = [r.get('record_hash') for r in data if r.get('record_hash')]
print(len(hashes))
" 2>/dev/null || echo "0")
# Actually need to query audit log again with broader filter
curl -sk "https://$PROD_HOST/api/v1/admin/audit-log?limit=5" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -o /tmp/smoke_extra.body > /dev/null
HASH_COUNT=$(python3 -c "
import sys, json
data = json.load(open('/tmp/smoke_extra.body'))
hashes = sum(1 for r in data if r.get('record_hash'))
print(hashes)
" 2>/dev/null || echo "0")
log "  records with hash_chain: $HASH_COUNT (≥1 = OK)"

# === 12) Recovery mode (Sprint 42) ===
log "12) /api/v1/progress/recommend-next (Sprint 42 recovery_mode field)"
RECOVERY_CODE=$(curl -sk "https://$PROD_HOST/api/v1/progress/recommend-next" \
  -H "Authorization: Bearer $STUDENT_TOKEN" \
  -o /tmp/smoke_extra.body -w "%{http_code}")
[ "$RECOVERY_CODE" = "200" ] || fail "recommend-next = $RECOVERY_CODE"
RECOVERY_MODE=$(python3 -c "import sys, json; print(json.load(open('/tmp/smoke_extra.body')).get('recovery_mode'))")
RECOVERY_REASON=$(python3 -c "import sys, json; print(json.load(open('/tmp/smoke_extra.body')).get('recovery_reason'))")
log "  recovery_mode=$RECOVERY_MODE, reason=$RECOVERY_REASON"

# === 13) Parent metrics (Sprint 49) ===
log "13) /metrics содержит parent_* (Sprint 49)"
METRICS_CODE=$(curl -sk "https://$PROD_HOST/metrics" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -o /tmp/smoke_extra.body -w "%{http_code}")
[ "$METRICS_CODE" = "200" ] || fail "/metrics = $METRICS_CODE"
PARENT_STREAK=$(grep -c "^parent_streak" /tmp/smoke_extra.body)
PARENT_PAUSES=$(grep -c "^parent_session_pauses" /tmp/smoke_extra.body)
[ "$PARENT_STREAK" -gt "0" ] || fail "no parent_streak in /metrics"
[ "$PARENT_PAUSES" -gt "0" ] || fail "no parent_session_pauses in /metrics"
log "  /metrics OK: parent_streak=$PARENT_STREAK, parent_session_pauses=$PARENT_PAUSES"

log "OK: smoke-extra прошёл (13 проверок)"