"""CLI для cron: отправка weekly summary всем родителям.

Запуск:
    python -m app.scripts.weekly_summary

Или руками:
    docker exec deploy-backend-1 python3 -m app.scripts.weekly_summary
"""
import logging
import sys

from app.config import get_settings
from app.db.session import SessionLocal
from app.notifications.weekly import send_weekly_summary_for_all_parents

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("weekly_summary")


def main() -> int:
    settings = get_settings()
    db = SessionLocal()
    try:
        count = send_weekly_summary_for_all_parents(db)
        logger.info("Weekly summary sent to %d parents", count)
        return 0
    except Exception:
        logger.exception("Weekly summary FAILED")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
