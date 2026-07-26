"""Sprint 16.0 + 50: Telegram alert worker.

Читает из Redis list `ai:alerts`, шлёт в Telegram с dedupe (5 мин на
status+method+path). Не блокирует HTTP middleware (в отличие от sync
httpx.post()).

Sprint 50 улучшения:
- Graceful drain on SIGTERM/SIGINT (process pending alerts перед exit).
- Persistent JSONL log в /var/log/ai-tutor/alerts.jsonl (для compliance).
- Exponential backoff для Redis reconnect (1 → 30 сек).
- Возврат message_id из send_telegram для persistent logging.

Запуск:
- Вручную: docker exec deploy-backend-1 python3 -m app.bot.alert_worker
- В фоне: supervisor в deploy/monitoring/telegram-bot.sh
- Cron каждые 5 мин: ai-tutor-telegram-bot.cron
"""
from __future__ import annotations

import json
import logging
import os
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
import redis
from redis import exceptions as redis_exceptions

logger = logging.getLogger("alert_worker")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_ALERT_CHAT_ID = os.environ.get("TELEGRAM_ALERT_CHAT_ID", "")
# Dedupe TTL: не отправлять одинаковые алерты чаще чем раз в N секунд.
ALERT_DEDUPE_TTL = int(os.environ.get("ALERT_DEDUPE_TTL", "300"))
ALERT_LIST_KEY = "ai:alerts"
ALERT_DEDUPE_PREFIX = "alert:dedupe:"
# Если Telegram не отвечает — ждём N сек.
ALERT_TELEGRAM_TIMEOUT = float(os.environ.get("ALERT_TELEGRAM_TIMEOUT", "5.0"))
# Sprint 50: persistent JSONL log (compliance).
ALERT_LOG_FILE = os.environ.get("ALERT_LOG_FILE", "/var/log/ai-tutor/alerts.jsonl")
# Sprint 50: max items в drain queue при shutdown.
ALERT_DRAIN_MAX_ITEMS = int(os.environ.get("ALERT_DRAIN_MAX_ITEMS", "50"))

_running = True
_shutdown_reason = "running"


def _signal_handler(sig, _frame):
    """Sprint 50: graceful shutdown с drain queue."""
    global _running, _shutdown_reason
    try:
        _shutdown_reason = signal.Signals(sig).name
    except (AttributeError, ValueError):
        _shutdown_reason = f"signal_{sig}"
    logger.info("alert_worker: received %s, draining queue...", _shutdown_reason)
    _running = False


signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)


def _log_to_file(payload: dict, status: str, telegram_message_id: int | None) -> None:
    """Sprint 50: persistent JSONL log (compliance/auditing).

    Создаёт директорию если нет. Пишет одну JSON строку = один alert.
    """
    try:
        log_path = Path(ALERT_LOG_FILE)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": status,  # sent | deduped | error
            "telegram_message_id": telegram_message_id,
            "payload": payload,
        }
        with log_path.open("a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.warning("Не удалось записать alert в файл %s: %s", ALERT_LOG_FILE, e)


def send_telegram(text: str) -> int | None:
    """Sprint 16.0 + 50: отправка в Telegram с коротким timeout.

    Returns:
        message_id при успехе, None при ошибке.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_ALERT_CHAT_ID:
        logger.warning("TELEGRAM_BOT_TOKEN или TELEGRAM_ALERT_CHAT_ID не установлены")
        return None
    try:
        r = httpx.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={
                "chat_id": TELEGRAM_ALERT_CHAT_ID,
                "text": text,
                "parse_mode": "HTML",
            },
            timeout=ALERT_TELEGRAM_TIMEOUT,
        )
        if r.status_code == 200:
            data = r.json()
            return data.get("result", {}).get("message_id")
        logger.warning("Telegram send failed: %s %s", r.status_code, r.text[:200])
        return None
    except Exception as e:
        logger.warning("Telegram send error: %s", e)
        return None


def format_alert(payload: dict) -> str:
    """Sprint 16.0: человекочитаемый формат для Telegram."""
    kind = payload.get("kind", "unknown")
    if kind == "http_5xx":
        method = payload.get("method", "?")
        path = payload.get("path", "?")
        status = payload.get("status", "?")
        req_id = payload.get("request_id", "?")
        return (
            f"🚨 <b>AI-Tutor 5xx</b>\n"
            f"Method: {method}\n"
            f"Path: {path}\n"
            f"Status: {status}\n"
            f"Request ID: {req_id}"
        )
    # generic
    return f"⚠ <b>AI-Tutor alert</b>\n<code>{json.dumps(payload, default=str)[:500]}</code>"


def process_one(r: redis.Redis, payload_str: str) -> bool:
    """Sprint 16.0 + 50: обработка одного alert с dedupe + persistent log.

    Returns True если отправлено, False если dedupe или ошибка.
    """
    try:
        payload = json.loads(payload_str)
    except json.JSONDecodeError:
        logger.warning("Invalid alert payload: %s", payload_str[:200])
        _log_to_file({"raw": payload_str[:200]}, "error", None)
        return False

    # Dedupe key: status+method+path
    dedupe_id = f"{payload.get('status', '')}:{payload.get('method', '')}:{payload.get('path', '')}"
    dedupe_key = f"{ALERT_DEDUPE_PREFIX}{dedupe_id}"
    # SET NX EX — только если не существует
    if not r.set(dedupe_key, "1", nx=True, ex=ALERT_DEDUPE_TTL):
        logger.info("Dedupe: %s — пропускаю", dedupe_id)
        _log_to_file(payload, "deduped", None)
        return False

    text = format_alert(payload)
    msg_id = send_telegram(text)
    if msg_id is not None:
        _log_to_file(payload, "sent", msg_id)
        return True
    _log_to_file(payload, "error", None)
    return False


def _drain_queue(r: redis.Redis, max_items: int = ALERT_DRAIN_MAX_ITEMS) -> int:
    """Sprint 50: process pending alerts перед exit (graceful drain)."""
    processed = 0
    while processed < max_items:
        try:
            payload_str = r.lpop(ALERT_LIST_KEY)
            if payload_str is None:
                break
            process_one(r, payload_str)
            processed += 1
        except redis_exceptions.ConnectionError:
            logger.warning("Drain: Redis connection error, aborting")
            break
    return processed


def main() -> int:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_ALERT_CHAT_ID:
        logger.error("TELEGRAM_BOT_TOKEN и TELEGRAM_ALERT_CHAT_ID обязательны")
        return 1

    r = redis.from_url(REDIS_URL, decode_responses=True)
    logger.info(
        "alert_worker: started (Redis=%s, dedupe_ttl=%ds, list=%s, log=%s, drain_max=%d)",
        REDIS_URL, ALERT_DEDUPE_TTL, ALERT_LIST_KEY, ALERT_LOG_FILE, ALERT_DRAIN_MAX_ITEMS,
    )

    # Sprint 50: exponential backoff для reconnect (1 → 30 сек).
    reconnect_delay = 1

    while _running:
        try:
            # BLPOP с timeout 1 сек — чтобы можно было прервать по сигналу
            result = r.blpop(ALERT_LIST_KEY, timeout=1)
            if result is None:
                continue
            _list_key, payload_str = result
            if process_one(r, payload_str):
                logger.info("Alert sent: %s", payload_str[:200])
            else:
                logger.warning("Alert skipped: %s", payload_str[:200])
            # Reset backoff на success.
            reconnect_delay = 1
        except redis_exceptions.ConnectionError as e:
            logger.error(
                "Redis connection error: %s. Reconnecting in %ds...", e, reconnect_delay
            )
            time.sleep(reconnect_delay)
            # Exponential backoff (max 30 сек).
            reconnect_delay = min(reconnect_delay * 2, 30)
        except Exception as e:
            logger.exception("Alert processing error: %s", e)
            time.sleep(1)

    # Sprint 50: graceful drain перед exit.
    logger.info("alert_worker: draining queue (max %d items)...", ALERT_DRAIN_MAX_ITEMS)
    drained = _drain_queue(r, max_items=ALERT_DRAIN_MAX_ITEMS)
    logger.info(
        "alert_worker: stopped (signal=%s, drained=%d)", _shutdown_reason, drained
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())