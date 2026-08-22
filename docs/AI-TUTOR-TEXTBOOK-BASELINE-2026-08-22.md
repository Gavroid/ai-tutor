# AI-Tutor — baseline учебников и репозитория

Дата: 2026-08-22 (срез после аудита, до изменения кода)
Рабочий каталог: `/root/workspace/ai-tutor`

> Read-only снимок состояния, без мутаций. Используется как gate для Stage 1+
> и как reference для evidence matrix. Production не трогали: `/health` и `/ready`
> отвечают `HTTP 200`, контейнеры работают с `2026-08-20T15:55:28Z`.

---

## 1. Репозиторий

| Поле | Значение |
|---|---|
| HEAD | `ac9739f4333a1f5ad83af2cf21629b793774cef9` |
| Branch | `design-audit-2026-08-20-fixes` |
| Modified (committed files) | `README.md`, `apps/backend/scripts/content_quality_baseline_audit.py`, `apps/backend/tests/test_content_quality_baseline_audit.py`, `apps/backend/tests/test_progress_diagnostics.py`, `apps/backend/tests/test_rag_integration.py`, `docs/ALL-SUBJECTS-PRODUCTION-READINESS-2026-08-19.md`, `docs/pilot-topic-matrix.md`, `docs/pilot-walkthrough-notes.md` |
| Untracked | `AUDIT_2026-08-22.md`, `data/`, `tmp/`, 9 файлов `docs/AI-TUTOR-*-2026-08-22.md` (включая handoff + next-session prompt), 3 презентации, `docs/design-audit-2026-08-20/`, `docs/design-audit-2026-08-22/` |

`git diff --check` — без warning'ов.

**Правила:** не делать `git reset --hard`, `git clean -fd`, массовое удаление, перезапись
`.env`, `secrets/`, `data/`, `tmp/` без явного разрешения.

## 2. Окружение

| Утилита | Путь |
|---|---|
| pdfinfo | `/usr/bin/pdfinfo` |
| pdftotext | `/usr/bin/pdftotext` |
| tesseract | `/usr/bin/tesseract` |
| ocrmypdf | `/usr/local/bin/ocrmypdf` |
| ssh | `/usr/bin/ssh` |
| docker / docker compose | **отсутствуют локально** |
| Local `.env` | `/root/workspace/ai-tutor/.env` (29 строк, PostgreSQL URL) |
| SSH key | `/root/.ssh/id_ed25519_kirill_ai` |

Backend venv: `/root/workspace/ai-tutor/apps/backend/.venv` — OK.
Frontend node_modules: `/root/workspace/ai-tutor/apps/frontend/node_modules` — OK.

Backend tests на `tests/test_health.py` локально зелёные: **8 passed**.

## 3. Production health (read-only)

```text
GET https://school.431a.ru/health
  {"status":"ok","service":"AI Tutor 7","env":"production","version":"0.1.0-mvp","uptime_seconds":181278,"started_at":"2026-08-20T15:55:28.904873+00:00"}
  HTTP=200

GET https://school.431a.ru/ready
  {"status":"ready"}
  HTTP=200
```

## 4. Учебники — sha256, pages, size, text-coverage

| Файл | Pages | Size (bytes) | Text@pp30-33 | Text total |
|---|---:|---:|---:|---:|
| `01-algebra-07-makarychev-2013.pdf` | 337 | 25 510 294 | 12 231 | 934 818 |
| `02-geometriya-7-9-atanasyan-2023.pdf` | 417 | 6 425 203 | 13 355 | 1 516 479 |
| `04-istoriya-rossii-07-2015.pdf` | 257 | 81 930 367 | 13 202 | 891 028 |
| `04-istoriya-rossii-07-2015-orig.pdf` | 257 | 61 393 195 | **4** | **257** |
| `05-vseobshchaya-istoriya-07-2012.pdf` | 340 | 250 841 300 | 14 541 | 1 122 198 |
| `05-vseobshchaya-istoriya-07-2012-orig.pdf` | 340 | 52 536 432 | **4** | **340** |
| `06-anglijskij-spotlight-07-ch1.pdf` | 102 | 168 586 310 | 14 621 | 428 011 |
| `07-russkij-07-baranov-ch1-2020.pdf` | 184 | 1 054 804 | 10 339 | 494 741 |
| `07-russkij-07-baranov-ch2-2020.pdf` | 148 | 822 441 | 13 302 | 390 613 |
| `08-literatura-07-korovina-ch1.pdf` | 273 | 6 923 776 | 8 769 | 907 741 |
| `09-biologiya-07-pasechnik-2022.pdf` | 193 | 74 791 747 | 9 687 | 456 514 |
| `10-fizika-07-peryshkin-2024.pdf` | 241 | 21 075 235 | 16 333 | 872 165 |
| `11-informatika-07-bosova-2023.pdf` | 257 | 28 005 686 | 12 492 | 836 518 |
| `11-informatika-07-bosova-2023-orig.pdf` | 257 | 46 615 076 | **4** | **257** |
| `12-obshchestvoznanie-07-bogolyubov-2023.pdf` | 144 | 33 547 999 | 15 942 | 589 819 |
| `12-obshchestvoznanie-07-bogolyubov-2023-orig.pdf` | 144 | 32 852 753 | **4** | **144** |
| `13-himiya-07-gabrielyan-2017.pdf` | 145 | 53 454 368 | 11 468 | 497 250 |
| `13-himiya-07-gabrielyan-2017-orig.pdf` | 145 | 36 960 628 | **4** | **145** |
| `14-literatura-07-korovina-ch2.pdf` | 289 | 4 956 353 | 10 691 | 1 045 315 |
| `15-geografiya-07-alekseev-2024.pdf` | 257 | 178 400 995 | 13 657 | 1 191 992 |

**Что важно:**

- Все 5 файлов `*-orig.pdf` имеют пустой text-layer (`text total ≈ pages`,
  по ~1 байту на страницу) — это image-only оригиналы, OCR на них ещё не выполнялся.
  Их нужно **сохранить как `*-orig.pdf`**, OCR-версии лежат рядом.
- Все остальные 15 PDF — text/OCR с плотным текстом. Покрытие 800KB–1.5MB текста
  для типичной книги, что соответствует OCR/text extraction.
- Самая тяжёлая книга по контенту — `02-geometriya-7-9-atanasyan-2023.pdf` (1.5MB текста
  на 6MB PDF) — нужна отдельная QA на диаграммы и обозначения.
- Самая большая по размеру — `15-geografiya-07-alekseev-2024.pdf` (178MB, OCR) —
  проблемная зона по картам 245–254.
- Сравнение OCR-версий (`05-vseobshchaya-istoriya-07-2012.pdf`, `04-istoriya-rossii-07-2015.pdf`,
  `11-informatika-07-bosova-2023.pdf`, `12-obshchestvoznanie-07-bogolyubov-2023.pdf`,
  `13-himiya-07-gabrielyan-2017.pdf`) с их `*-orig.pdf` показывает: OCR-слой даёт
  **реальный текст**, но плотность меньше, чем у text-layer книг; это ожидаемо
  и потребует visual QA для формул/таблиц/кода.

Полные sha256 сохранены в `/tmp/ai-tutor-baseline/textbook-sha256.txt`.

## 5. Curriculum anchors

`data/textbooks/grade7-curriculum/` содержит 10 файлов (ФРП/ФООП/перечни) — это
**reference**, не учебники. Не использовать как замену источнику.

`data/textbooks/grade7-humanities/` — дубли curriculum и служебные `.md` заметки.
Не считать отдельными оригиналами учебников.

## 6. Текущий readiness — критичный риск

`apps/backend/app/subjects/router.py` (lines 28–47) содержит:

```python
MVP_READY_SUBJECT_KEYWORDS = ("математика", "6 класс", "повтор")
...
ready = all(word in normalized for word in MVP_READY_SUBJECT_KEYWORDS)
if ready:
    return {"mvp_status": "mvp_ready", "rag_ready": True, "practice_ready": True, ...}
```

И затем (lines 113–118) для всех остальных subjects:

```python
if base["route_ready"] and base["rag_ready"] and base["practice_ready"]:
    base["mvp_status"] = "mvp_ready"
```

Это означает: **любой subject с route + practice + source coverage по всем темам**
(а это seed topics + seed route + seeded fallback-bank) автоматически получает
`mvp_ready=true` в `/api/v1/subjects`. Это именно та ложная готовность, от которой
план просит защититься.

**Gate Stage 2:** убрать keyword-ветку и автоматическое повышение по counts,
ввести явные evidence-поля, policy fail-closed, тесты.

## 8. Снимок baseline

Артефакты (read-only):

- `/tmp/ai-tutor-baseline/git-status.txt` — git status + HEAD + branch
- `/tmp/ai-tutor-baseline/textbook-sha256.txt` — sha256 всех 20 PDF
- `/tmp/ai-tutor-baseline/textbook-pages.txt` — pages/size/text-coverage