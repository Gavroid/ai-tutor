# Textbook license review DRAFT (2026-08-23)

## Status: DRAFT — не для apply без operator review

Эта таблица — предложение по `license_decision` для 20 manifest rows
(`data/textbooks/7-class/textbook-manifest.csv`). Все 20 строк сейчас
имеют `license_decision=needs_review` (см. audit 2026-08-23).

**Не применяется автоматически.** Применяется после ручной проверки
operator'ом (юрист + администратор платформы).

## Метод

Для каждой строки manifest оцениваю:
1. `source_kind` (internal_scan / ocr / pdf_native).
2. `subject_code` + `title` + автор (если есть).
3. Год выпуска (если известен).
4. Типичный publisher для school textbooks (РФ, 7 класс).
5. Возможный license outcome (НЕ юридическая оценка — флаги для review).

## Sub-states

На основании типичной ситуации для школьных учебников 7 класса РФ:

| `source_kind` | Recommended review path |
|---|---|
| `internal_scan` (parent_owned) | parent предоставил скан; license = parent-owned, distribution needs written consent. |
| `ocr` (no parent scan) | выгрузка из external текста; license = TBD per source URL. |
| `pdf_native` (publisher-provided) | publisher license applies. |

⚠️ Эти рекомендации **НЕ юридическая консультация**. Operator должен
сверить с реальными source URLs и принять решение.

## Table (20 rows)

| subject_code | year | source_kind | recommended_status | rationale |
|---|---|---|---|---|
| algebra | 2013 | internal_scan | parent_owned → fair_use_education | parent scan of Makarychev 2013 (mass distribution textbook) |
| geom | 2023 | internal_scan | parent_owned → fair_use_education | parent scan Atanasyan 2023 |
| hist (orig+ocr) | 2015 | ocr → text_layer | fair_use_education candidate | OCR derived from publisher PDF, РФ гос. school textbook |
| hist-world (orig+ocr) | 2012 | ocr → text_layer | fair_use_education candidate | same as hist |
| eng | 0 | ocr | needs_review (publisher-dependent) | Spotlight — foreign publisher, per-file |
| rus (Баранов ч1, ч2) | 2020 | text_layer | fair_use_education | publisher textbook |
| lit (Коровина ч1) | 0 | text_layer | fair_use_education | publisher textbook |
| bio (Пасечник) | 2022 | text_layer | fair_use_education | publisher textbook |
| phys (Пёрышкин) | 2024 | text_layer | fair_use_education | publisher textbook |
| inf (orig+text) | 2023 | mixed | fair_use_education | publisher textbook |
| soc (orig+text) | 2023 | mixed | fair_use_education | publisher textbook (Bogolyubov) |
| chem (orig+text) | 2017 | mixed | fair_use_education | publisher textbook (Gabrielyan) |
| lit (Коровина ч2) | 0 | text_layer | fair_use_education | publisher textbook |
| geo (Алексеев) | 2024 | text_layer | fair_use_education | publisher textbook |

## Что НЕ сделано в этом draft

- Не применён ни один `license_decision` к manifest.
- Не запрошены реальные source URLs (это дано в `source_url` колонке
  manifest, требует визита на `https://school.431a.ru/...`).
- Не оценены изображения (репродукции, карты) — отдельная подкатегория
  в `image_only` rows (5/20), это Sprint 6 OCR-Risk territory.
- Не оценены translated/works (Spotlight = en, Атанасян /etc = ru).

## Что делать дальше (operator action)

1. Operator открывает `data/textbooks/7-class/textbook-manifest.csv`.
2. Для каждой строки принимает решение: `fair_use_education` (использовать
   в pilot) или `blocked_license` (не использовать до получения rights).
3. После apply — пересборка evidence validator (см. S3 policy).
4. Re-run `python -m app.subjects.evidence_schema evidence.json` для
   sanity check.

## Reference

- Audit 2026-08-23: docs/AI-TUTOR-AUDIT-CURRENT-2026-08-23.md
  §3 «Лицензионный статус текущего manifest не разрешён».
- Sprint 5 Definition of Done §"licenses resolved" — debt.
- SPDX license list: https://spdx.org/licenses/ (для spec строк).
