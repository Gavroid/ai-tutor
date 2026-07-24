"""Sprint 16.0 P0-4: Telegram alert worker.

Читает из Redis list `ai:alerts`, шлёт в Telegram с dedupe (5 мин на
status+method+path). Не блокирует HTTP middleware (в отличие от sync
httpx.post()).

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

import httpx
import redis

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

_running = True


def _signal_handler(_sig, _frame):
    global _running
    logger.info("alert_worker: received signal, stopping...")
    _running = False


signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)


def send_telegram(text: str) -> bool:
    """Sprint 16.0: отправка в Telegram с коротким timeout."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_ALERT_CHAT_ID:
        logger.warning("TELEGRAM_BOT_TOKEN или TELEGRAM_ALERT_CHAT_ID не установлены")
        return False
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
            return True
        logger.warning("Telegram send failed: %s %s", r.status_code, r.text[:200])
        return False
    except Exception as e:
        logger.warning("Telegram send error: %s", e)
        return False


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
    """Sprint 16.0: обработка одного alert с dedupe.

    Returns True если отправлено, False если dedupe или ошибка.
    """
    try:
        payload = json.loads(payload_str)
    except json.JSONDecodeError:
        logger.warning("Invalid alert payload: %s", payload_str[:200])
        return False

    # Dedupe key: status+method+path
    dedupe_id = f"{payload.get('status', '')}:{payload.get('method', '')}:{payload.get('path', '')}"
    dedupe_key = f"{ALERT_DEDUPE_PREFIX}{dedupe_id}"
    # SET NX EX — только если не существует
    if not r.set(dedupe_key, "1", nx=True, ex=ALERT_DEDUPE_TTL):
        logger.info("Dedupe: %s — пропускаю", dedupe_id)
        return False

    text = format_alert(payload)
    return send_telegram(text)


def main() -> int:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_ALERT_CHAT_ID:
        logger.error("TELEGRAM_BOT_TOKEN и TELEGRAM_ALERT_CHAT_ID обязательны")
        return 1

    r = redis.from_url(REDIS_URL, decode_responses=True)
    logger.info(
        "alert_worker: started (Redis=%s, dedupe_ttl=%ds, list=%s)",
        REDIS_URL, ALERT_DEDUPE_TTL, ALERT_LIST_KEY,
    )

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
        except redis.exceptions.ConnectionError as e:
            logger.error("Redis connection error: %s. Reconnecting in 5s...", e)
            time.sleep(5)
        except Exception as e:
            logger.exception("Alert processing error: %s", e)
            time.sleep(1)

    logger.info("alert_worker: stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
