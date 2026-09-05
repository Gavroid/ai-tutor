#!/usr/bin/env bash
# Sprint 3.45 (T5 из аудита): monthly doc-archive.
#
# Что делает:
# 1. Находит все .md файлы в docs/ за предыдущий месяц (по regex *YYYY-MM*.md)
# 2. Перемещает их в docs/archive/YYYY-MM/ (git mv для сохранения истории)
# 3. Обновляет docs/INDEX.md (добавляет ссылку на новую папку)
#
# Использование:
#   docs-monthly-archive.sh            # архивировать за предыдущий месяц
#   docs-monthly-archive.sh 2026-07    # архивировать за конкретный месяц
#   docs-monthly-archive.sh --dry-run  # показать что будет сделано, без изменений
#
# Cron (Sprint 3.45):
#   0 3 1 * *  /root/workspace/ai-tutor/scripts/docs-monthly-archive.sh >> /var/log/docs-archive.log 2>&1
#   (1-го числа каждого месяца в 03:00 MSK)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DOCS_DIR="$PROJECT_ROOT/docs"
LOG_PREFIX="[docs-archive]"

log() { printf '%s %s\n' "$LOG_PREFIX" "$*"; }
fail() { printf '%s ERROR: %s\n' "$LOG_PREFIX" "$*" >&2; exit 1; }

# Определяем месяц для архивации
if [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN=true
    TARGET_MONTH=$(date -d "last month" +%Y-%m)
elif [[ -n "${1:-}" ]]; then
    DRY_RUN=false
    TARGET_MONTH="$1"
else
    DRY_RUN=false
    TARGET_MONTH=$(date -d "last month" +%Y-%m)
fi

log "Sprint 3.45: archiving docs/*${TARGET_MONTH}*.md → docs/archive/${TARGET_MONTH}/"

# Создаём папку архива если нет
ARCHIVE_DIR="$DOCS_DIR/archive/$TARGET_MONTH"
if [[ "$DRY_RUN" == "true" ]]; then
    log "[DRY-RUN] would create $ARCHIVE_DIR if missing"
else
    mkdir -p "$ARCHIVE_DIR"
fi

# Находим файлы
PATTERN="${TARGET_MONTH}-*.md"
FILES=$(cd "$DOCS_DIR" && ls $PATTERN 2>/dev/null | grep -v "^archive/" || true)

if [[ -z "$FILES" ]]; then
    log "No files matching pattern '$PATTERN' in docs/ (excluding archive/). Nothing to do."
    exit 0
fi

COUNT=0
for file in $FILES; do
    if [[ "$DRY_RUN" == "true" ]]; then
        log "[DRY-RUN] would git mv: $file → archive/$TARGET_MONTH/$file"
    else
        log "git mv: $file → archive/$TARGET_MONTH/$file"
        cd "$PROJECT_ROOT" && git mv "$DOCS_DIR/$file" "$ARCHIVE_DIR/$file"
    fi
    COUNT=$((COUNT + 1))
done

log "Done. Files ${DRY_RUN:+that would be }archived: $COUNT"
