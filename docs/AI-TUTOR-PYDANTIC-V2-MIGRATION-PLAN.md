# Pydantic V1 → V2 миграция — backlog (2026-08-23)

## Status: частично выполнено в sprint-continuation (2026-08-23)

### Что сделано в T1.3c

- `apps/backend/app/teacher/schemas.py`: `class Config: from_attributes = True`
  → `model_config = ConfigDict(from_attributes=True)`.
- `apps/backend/app/invites/router.py`: то же.

Это закрывает **только наши** `class Config` вхождения в `app/`.

### Что осталось (debt, не блокер для Sprint 1–8 close-out)

1. **`pydantic._internal._config:295` DeprecationWarning** всё ещё
   присутствует в regression-выводе. Это shared warning, идёт из
   pydantic-core 2.x на каждый импорт `BaseModel`. Наш код перевёл
   `class Config:` → `model_config = ConfigDict(...)` — но warning
   не от нашего кода, а от V2 internals (миграционный шум,
   удалится в pydantic V3).

2. **Полный sweep** по `class Config`:
   ```
   grep -rn 'class Config' /root/workspace/ai-tutor --include='*.py'
   ```
   На момент T1.3c найдено 2 вхождения в нашем коде, оба закрыты.
   Если есть в `/root/workspace/nightscout/` или `/opt/ai-tutor/`
   — это вне scope (production/sibling), не трогаем.

3. **Pydantic V1 support timeline**: Pydantic V2 — текущая major.
   Pydantic V3 ожидается в 2025–2026, ломает многое. Переход на
   V3 — отдельный спринт P2.

### Когда возвращаться

- Когда pytest warnings перестанут молчать passlib/sqlalchemy
  deprecation (✅ уже) и юзер захочет чистый CI log;
- Когда pydantic V2 line в requirements-dev.txt устареет
  (Pydantic 2.x → 3.x);
- Когда появится потребность в новых Pydantic V2 фичах
  (например field discriminators, more strict types).

### Reference

- Sprint plan §"Definition of Done для автоматического pilot":
  > Известные ограничения задокументированы.
- Релиз этого backlog: `chore(sprint-continuation): ...` commit
  сразу после `c77a92e`.
