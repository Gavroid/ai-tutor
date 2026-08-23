#!/usr/bin/env bash
# Sprint 1 (2026-08-23): backend suite runner.
# Делит tests/ на группы и запускает каждую с дедлайном, чтобы timeout
# не маскировал неизвестный остаток suite.
#
# Использование:
#   ./scripts/run_backend_groups.sh            # все группы
#   ./scripts/run_backend_groups.sh core       # только указанные префиксы
#
# Выход:
#   Код 0 — все запрошенные группы прошли.
#   Код !=0 — хотя бы одна группа вернула non-zero или была killed по таймауту.

set -uo pipefail

cd "$(dirname "$0")/.."

PYTEST=".venv/bin/pytest"
TIMEOUT_BIN="$(command -v timeout || true)"
if [[ -z "$TIMEOUT_BIN" ]]; then
    echo "FATAL: 'timeout' command not found in PATH" >&2
    exit 2
fi

# Per-group wall-clock budget (seconds). Можно переопределить через env.
CORE_BUDGET="${CORE_BUDGET:-300}"
LONG_BUDGET="${LONG_BUDGET:-540}"

# Префиксы групп (имя файла без .py). match=core|all|long.
CORE_GROUPS=(
    "test_subjects"
    "test_chunker"
    "test_health"
    "test_admin_evidence"
    "test_admin"
)

LONG_GROUPS=(
    "test_ai"
    "test_ai_generate_uses_topic_fallback"
    "test_ai_output_contract"
    "test_ai_output_regression_pack"
    "test_progress_diagnostics"
    "test_rag"
    "test_rag_integration"
    "test_rag_metadata_audit"
    "test_rag_metadata_backfill"
    "test_auth"
    "test_websocket"
    "test_voice"
    "test_teacher"
    "test_algebra"
    "test_geometry"
    "test_pilot"
    "test_p0_followup_seed"
    "test_notifications"
    "test_oauth"
    "test_ops_metrics"
    "test_observability"
    "test_login_rate_limit"
    "test_diagnostic_expire"
    "test_alert_worker"
    "test_email"
    "test_sprint"
    "test_stage6"
    "test_techdebt"
    "test_remaining_subjects"
    "test_learning_analytics"
    "test_parent"
    "test_refresh"
    "test_password_reset"
    "test_rbac"
    "test_audit_retention"
    "test_student_review"
    "test_telegram_bot"
    "test_ws_rate_limit"
    "test_math_"
    "test_ocr"
)

run_group() {
    local pattern="$1"
    local budget="$2"
    # Составляем glob-pattern по префиксу: tests/${pattern}*.py
    local files
    files=$(ls tests/${pattern}*.py 2>/dev/null || true)
    if [[ -z "$files" ]]; then
        printf 'SKIP  %s (no files)\n' "$pattern"
        return 0
    fi
    local log="/tmp/pytest-group-${pattern}.log"
    local t0 t1 rc duration
    t0=$(date +%s)
    # shellcheck disable=SC2086
    "$TIMEOUT_BIN" "$budget" "$PYTEST" -q --no-header \
        -p no:cacheprovider --durations=20 $files \
        >"$log" 2>&1
    rc=$?
    t1=$(date +%s)
    duration=$((t1 - t0))
    if [[ $rc -eq 0 ]]; then
        # Извлекаем сводку.
        local summary
        summary=$(grep -E '[0-9]+ (passed|failed|skipped)' "$log" | tail -1 || echo "no summary")
        printf 'OK    %-40s %4ds  %s\n' "$pattern" "$duration" "$summary"
        return 0
    fi
    if [[ $rc -eq 124 ]]; then
        printf 'TIMEOUT %-38s %4ds  budget=%ss (see /tmp/pytest-group-%s.log)\n' \
            "$pattern" "$duration" "$budget" "$pattern"
        return 124
    fi
    local summary
    summary=$(grep -E '(FAILED|ERROR)' "$log" | head -3 || echo "")
    printf 'FAIL  %-40s rc=%d %4ds\n' "$pattern" "$rc" "$duration"
    [[ -n "$summary" ]] && printf '       %s\n' "$summary"
    return 1
}

mode="${1:-all}"
total_fail=0

case "$mode" in
    core)
        groups=("${CORE_GROUPS[@]}")
        budgets=()
        for _ in "${groups[@]}"; do budgets+=("$CORE_BUDGET"); done
        ;;
    all)
        groups=("${CORE_GROUPS[@]}" "${LONG_GROUPS[@]}")
        budgets=()
        # Core-группы короткие — короткий бюджет; остальные — длинный.
        for g in "${CORE_GROUPS[@]}"; do budgets+=("$CORE_BUDGET"); done
        for _ in "${LONG_GROUPS[@]}"; do budgets+=("$LONG_BUDGET"); done
        ;;
    *)
        echo "Usage: $0 [core|all]" >&2
        exit 2
        ;;
esac

echo "=== backend suite groups (mode=$mode) ==="
echo "core_budget=${CORE_BUDGET}s  long_budget=${LONG_BUDGET}s"
for i in "${!groups[@]}"; do
    g="${groups[$i]}"
    b="${budgets[$i]}"
    run_group "$g" "$b" || total_fail=$((total_fail + 1))
done
echo "=== done: total_fail=$total_fail ==="
exit $(( total_fail > 0 ? 1 : 0 ))
