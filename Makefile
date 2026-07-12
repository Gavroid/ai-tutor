# Удобные команды для локальной разработки.
# Запуск: make up / make down / make logs / make test / make migrate ...

.PHONY: help up down logs ps build rebuild migrate test backend-test frontend-install

help:
	@echo "Доступные команды:"
	@echo "  make up              — собрать и поднять весь стек"
	@echo "  make down            — остановить стек"
	@echo "  make logs            — логи всех сервисов"
	@echo "  make ps              — статус контейнеров"
	@echo "  make build           — пересобрать образы"
	@echo "  make rebuild         — пересобрать без кэша"
	@echo "  make migrate         — применить миграции Alembic"
	@echo "  make test            — backend pytest"
	@echo "  make backend-shell   — зайти в контейнер backend"
	@echo "  make db-shell        — psql в контейнере db"

up:
	cd deploy && cp -n ../.env.example ../.env || true && docker compose up -d --build

down:
	cd deploy && docker compose down

logs:
	cd deploy && docker compose logs -f --tail=100

ps:
	cd deploy && docker compose ps

build:
	cd deploy && docker compose build

rebuild:
	cd deploy && docker compose build --no-cache

migrate:
	cd deploy && docker compose exec backend alembic upgrade head

test:
	cd deploy && docker compose exec backend pytest -q

backend-test:
	cd apps/backend && python3 -m venv .venv && . .venv/bin/activate && pip install -q -r requirements-dev.txt && pytest -q

backend-shell:
	cd deploy && docker compose exec backend bash

db-shell:
	cd deploy && docker compose exec db psql -U $$POSTGRES_USER -d $$POSTGRES_DB

backup:
	bash deploy/backup/backup.sh