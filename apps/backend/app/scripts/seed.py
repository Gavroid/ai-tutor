"""Seed-скрипт: заполняет БД учебной программой 7 класса.

Запуск (внутри контейнера):
    cd /app && python -m app.scripts.seed

Опции:
    --reset   удалить существующие данные перед заполнением
    --dry-run показать, что будет сделано, без записи в БД
"""
from __future__ import annotations

import argparse
import sys

from app.db.session import SessionLocal
from app.subjects.scripts_seed_runner import seed_for_tests as _seed


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed учебной программы 7 класса")
    parser.add_argument("--reset", action="store_true", help="Удалить старые данные")
    parser.add_argument("--dry-run", action="store_true", help="Без записи в БД")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.dry_run:
            print("(dry-run) Будет удалено и пересоздано.")
            return 0
        n = _seed(db, reset=args.reset)
        print(f"✅ Создано {n} записей.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())