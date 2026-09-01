# AI-Tutor — аудит и план 2026-08-31 (индекс пакета)

**Цель работы:** довести проект до MVP-тестирования по всем предметам для одного ученика под контролем одного родителя.

## Файлы пакета

1. **`01-audit-full-2026-08-31.md`** — подробный итог аудита: свежие проверки (prod, БД, 1338+2 тестов), архитектура, контентная цепочка по предметам, 10 противоречий данных, 15 рисков, гэп-анализ цели.
2. **`02-development-plan-2026-08-31.md`** — план разработки **v2** (обновлён по ответам стейкхолдера 31.08: все 16 предметов, AI-first, геймификация, педагогический ИИ-слой).
3. **`03-sprint-stage-plan-2026-08-31.md`** — поэтапный план **v2**: спринты S0–S7 с acceptance criteria (~6 недель, качество > скорость).
4. **`04-stakeholder-questions-top25-2026-08-31.md`** — вопросы стейкхолдеру. ✅ **Отвечено 31.08.**
5. **`05-stakeholder-decisions-2026-08-31.md`** — зафиксированные решения владельца (нормативный документ D1–D5).
6. **`06-readiness-criteria-2026-08-31.md`** — критерии приёмки плана (RC-A…RC-G, 100% ✅ = MVP стартует).
7. **`07-NEXT-SESSION-PROMPT.md`** — самодостаточный промт для запуска разработки в новой сессии.

## Главный вывод

Код и инфраструктура готовы к MVP на ~85%. Блокер — контентная цепочка (0/16 предметов прошли полный конвейер) и непринятые продуктовые решения. Быстрый честный путь: открыть все предметы в AI-режиме с ярлыком качества, дожать математику до textbook-grade, дать родителю минимум одну контрольную функцию. Решения — за стейкхолдером (файл 04).

## Свежие факты (2026-08-31)

- Prod: health/ready 200; 16 предметов в API, открыт только math.
- Prod БД: 17 users, 16 subjects, 280 topics, 1637 rag_chunks, 479 attempts, alembic 0021.
- Backend tests: **1340 passed / 0 failed / 30 skipped** (Sprint S0, после фикса test_all_subject_contracts module-level env).
- Checkout: грязный (25 modified, ~107 untracked) — закрыто в Sprint S0 (см. `AI-TUTOR-SPRINT-S0-REPORT-2026-09-01.md`).
- S2: **263/263 topics × ≥10 fallback = 2630 practice tasks** (см. `AI-TUTOR-SPRINT-S2-S3-REPORT-2026-09-01.md`).
- S3: multi-explain (6 styles) + offtopic-guard + honest refuse + Socratic. 24/24 unit tests.
- **Production deploy 2026-09-01**: `https://school.431a.ru` жив, /health/ready/api/v2/health = 200, **280/280 topics practice coverage**, smoke основной PASSED. 5 fix-операций на проде (см. `AI-TUTOR-DEPLOY-REPORT-2026-09-01.md`).

Исторические аудиты (только как история): `docs/audit-2026-08-23/`, `docs/AI-TUTOR-FINAL-POST-EXECUTION-AUDIT-2026-08-25.md`.
