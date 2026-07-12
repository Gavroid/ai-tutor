#!/usr/bin/env python3
"""Sprint 4.2 — cron-задача: ежедневная очистка audit_logs.

Запуск:
  - через cron: 0 3 * * * /opt/ai-tutor/deploy/cron/audit_cleanup.py
  - вручную:    python3 audit_cleanup.py [--ttl-days 90] [--dry-run]

Что делает:
  - Подключается к БД через переменные окружения (DATABASE_URL)
  - Удаляет записи старше TTL (по умолчанию 90 дней)
  - Пишет лог в stdout (cron отправит на email)
  - Завершается с кодом 0 даже если записей нет

Переменные окружения:
  DATABASE_URL  — обязательно (например, postgresql://user:pass@host:5432/db)
  AUDIT_TTL_DAYS — опционально (по умолчанию 90)
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit log retention cleanup")
    parser.add_argument(
        "--ttl-days",
        type=int,
        default=int(os.environ.get("AUDIT_TTL_DAYS", "90")),
        help="Удалить записи старше N дней (по умолчанию 90)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Показать что будет удалено, но не удалять",
    )
    args = parser.parse_args()

    if not os.environ.get("DATABASE_URL"):
        print("ERROR: DATABASE_URL не задан", file=sys.stderr)
        return 1

    # Ленивая загрузка — только если БД нужна
    from sqlalchemy import create_engine, delete, func, select

    from app.admin import models as admin_models
    from app.config import get_settings
    from app.db.session import Base

    # Подгружаем все модели (для Base.metadata)
    from app.users import models as _u  # noqa
    from app.subjects import models as _s  # noqa
    from app.progress import models as _p  # noqa
    from app.diagnostics import models as _d  # noqa
    from app.notifications import models as _n  # noqa
    from app.auth import password_reset_models as _pr  # noqa

    settings = get_settings()
    engine = create_engine(settings.database_url)

    cutoff = datetime.now(timezone.utc) - timedelta(days=args.ttl_days)

    with engine.begin() as conn:
        # Сколько записей под удаление
        count_q = select(func.count(admin_models.AuditLog.id)).where(
            admin_models.AuditLog.created_at < cutoff
        )
        will_delete = conn.execute(count_q).scalar() or 0

        if args.dry_run:
            print(
                f"[dry-run] Будет удалено {will_delete} записей старше "
                f"{cutoff.isoformat()} (TTL={args.ttl_days}д)"
            )
            return 0

        if will_delete == 0:
            print(
                f"[{datetime.now(timezone.utc).isoformat()}] Нет записей для удаления "
                f"(TTL={args.ttl_days}д)"
            )
            return 0

        result = conn.execute(
            delete(admin_models.AuditLog).where(
                admin_models.AuditLog.created_at < cutoff
            )
        )
        deleted = int(result.rowcount or 0)

    print(
        f"[{datetime.now(timezone.utc).isoformat()}] "
        f"Удалено {deleted} audit_logs старше {cutoff.isoformat()} "
        f"(TTL={args.ttl_days}д)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
