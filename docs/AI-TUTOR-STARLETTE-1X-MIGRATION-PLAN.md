# Starlette 0.41 → 1.3.1 migration plan (2026-08-23)

## Статус

**Не применено.** Это migration plan + risk assessment. Реальный
upgrade требует отдельного sprint.

## Зачем

`apps/backend/.venv` Starlette **0.41.3**. pip-audit
(`AI-TUTOR-DEPENDENCY-AUDIT-2026-08-23.md`) показывает **9 CVE**:

| ID | Severity | Описание |
|---|---|---|
| CVE-2026-48710 | **HIGH** | Host header → request.url.path bypass |
| CVE-2026-54282 | MEDIUM | Path без `/` → request.url.hostname attacker-controlled |
| CVE-2026-54283 | MEDIUM | max_fields=max_part_size не enforced для urlencoded |
| CVE-2026-48818 | MEDIUM | StaticFiles на Windows → SMB credential leak |
| CVE-2026-48817 | MEDIUM | HTTPEndpoint method attribute bypass |
| CVE-2025-62727 | MEDIUM | ReDoS в FileResponse Range parser |
| CVE-2025-54121 | LOW | StaticFiles large file → event thread block |
| CVE-2026-1941 | LOW | Multipart spool blocking |
| CVE-2026-161 | HIGH | Host header validation (см. 48710) |

(см. полный список в audit)

## Где мы используем Starlette API

Grep по `apps/backend/{app,tests}`:

| API | Hits |
|---|---|
| `Request` | 26 |
| `Response` | 19 |
| `WebSocket` | 22 |
| `WebSocketDisconnect` | 8 |

**НЕ используем:** `FileResponse`, `StaticFiles`, `BackgroundTask`,
`Form parsing через parse_options`, `Middleware` классы.

Это **nodeploy** scope: меньше surface чем даже типичный Starlette
проект. Migration должна быть tractable.

## Основные breaking changes 0.41 → 1.3

### 1. `request.url` host validation (CVE-2026-48710, fix 1.0.1)

**0.41:** `request.url = "{scheme}://{Host-header}{path}"` reconstructed.
**1.0+:** Host header validated against RFC 9112 §3.2 grammar;
fallback `scope["server"]` для malformed.

**Наш impact:**
- `apps/backend/app/auth/security.py` — token in query string?
- `apps/backend/app/oauth*` — authorization code + redirect_uri
  проверка через `request.url`. **TBD high-risk**: любая
  redirect/host проверка может regression.
- Все 26 использований `Request` нужно re-audit.

### 2. `request.url.hostname`/`netloc` (CVE-2026-54282, fix 1.3.0)

**0.41:** path без `/` (напр. `@google.com`) → `request.url.hostname="google.com"`.
**1.3+:** path начинается с `/` enforced или fallback.

**Наш impact:** потенциальные SSRF-protection коды читающие
`request.url.hostname`.

### 3. multipart form limits (CVE-2026-54283, fix 1.3.1)

**0.41:** max_fields/max_part_size enforced для multipart но
**silently ignored** для urlencoded.
**1.3.1+:** enforced для обоих.

**Наш impact:** если мы лимитировали urlencoded-поглощение через
эти параметры — теперь реально ограничивается.

### 4. StaticFiles Windows SSRF (CVE-2026-48818, fix 1.1.0)

**Impact:** 0 (мы НЕ используем StaticFiles).

### 5. `Form.max_part_size` defaults

API change defaults may shift; behavior changes.

## Migration plan (пошаговый, для будущего sprint'а)

### Pre-migration (2-4 часа)

1. Создать ветку `feature/starlette-upgrade-1.3.1` от текущего HEAD.
2. Bump `starlette==1.3.1` в `requirements.txt`.
3. Прогнать `pytest tests/ -x` — собрать список **первого** failure.
4. Не пытаться fix'ить cascade. Каждое failure → отдельная запись.

### Phase 1: критические URL/host regressions (1-2 часа)

5. Audit all 26 `Request`-usage мест:
   ```bash
   grep -rn 'request\.url\|req\.url' apps/backend/app/ | grep -v test_
   ```
6. Categorize: read-only metadata? security gate? redirect target?
7. Для security gates — добавить regression test:
   - Host header attack (HTTP_HOST=evil.example.com/foo)
   - Path-based bypass (`GET @google.com`)
   - **Каждый** security critical → новый test class.
8. Regress на disposables, evidence schema, retry-safety.

### Phase 2: WS regressions (1-2 часа)

9. Прогнать `tests/test_websocket.py` + `test_ws_rate_limit.py` +
   `test_sprint27_cookie_auth.py` + все WS tests в sprint-*.
10. Если auth_handshake ломается — fix вручную через staticmethod
    class (новый style в starlette 1.x).
11. WebSocketDisconnect — проверить что path exception поднимается
    через chain.

### Phase 3: Edge case sweep (1-2 часа)

12. Прогнать `apps/frontend` typecheck (если задеваем WS контракты).
13. Прогнать `test_sprint*/` пакет на fragmentation.
14. **Проверить upload-path limits** — приложение использует
    multipart для upload → max_part_size стала enforced.
    Если max_part_size default не подходит — set explicit.

### Phase 4: deprecated path (30 мин)

15. Заменить любые deprecated Starlette API calls на новые.
16. Снять warnings filter для **upstream starlette** в pytest.ini —
    они должны быть silent после upgrade.

### Phase 5: dependency tree bump (1 час)

17. После starlette 1.3.1 — `fastapi` имеет ли свою совместимую
    pin? Проверить `pip install fastapi starlette` resolution.
18. `cryptography` allows 50.0+ (Bleichenbacher CVE-2026-69247 close)?
19. `python-multipart` — нужна ли min version? (закрывает 6 CVE
    параллельно).

### Phase 6: actual upgrade + verification (2-3 часа)

20. `starlette==1.3.1` + `fastapi` track + `cryptography>=50`
    + `python-multipart>=0.0.31` in `requirements.txt`.
21. `pip install --quiet -r requirements.txt` локально.
22. Прогнать все audit categories по новой.
23. **Re-run pip-audit**:
    ```
    $ .venv/bin/python -m pip_audit --skip-editable | head -20
    ```
    Ожидаемая дельта: **−9 starlette CVE**, плюс ещё −1/−2 от paired.
24. Smoke regression: 240 + новые tests должны проходить.

### Phase 7: deployment (1 час)

25. Production `/opt/ai-tutor` rebuild only после **manual
    verification** в disposable CI.
26. **Не auto-deploy** в production — Starlette 1.x = major version,
    требует manual sign-off.

## Что я **точно НЕ** делаю в этом plan'е

- ❌ Не upgrade'ю starlette в текущей ветке.
- ❌ Не применяю changes к `requirements.txt` для starlette.
- ❌ Не меняю `pyproject.toml` deps (не существует).
- ❌ Не делаю speculative fixes под возможный 1.x.

## Risk summary

| Risk | Probability | Severity | Mitigation |
|---|---|---|---|
| Mass test breakage | HIGH | HIGH | Phase 1-3 пошагово, не делать big-bang |
| Security regression в URL handling | MEDIUM | HIGH | Phase 1 audit + regression tests |
| Production deploy rollback нужен | HIGH | HIGH | Disposable CI first, не auto-deploy |
| FastAPI dep resolution conflict | MEDIUM | MEDIUM | Phase 5 explicit resolution check |
| WebSocket protocol edge case | LOW | HIGH | Phase 2 explicit WS regression |

## Estimate

Total: **8-12 hours** (one focused sprint, ideally with disposable
CI runner).

## Когда возвращаться

Этот plan автоматически стареет. Пересмотр требуется при:

- **fastapi 0.116+** release (хочет starlette ≥1.0).
- **starlette 1.4+** release (новые CVE могут быть).
- **Команда берёт disposable CI runner** в эксплуатацию — тогда
  реальный upgrade имеет смысл.
- **Security incident** linked to URL handling — immediate upgrade.

## References

- pip-audit snapshot: `AI-TUTOR-DEPENDENCY-AUDIT-2026-08-23.md`.
- starlette advisory feed: https://github.com/encode/starlette/security/advisories
- starlette changelog: https://github.com/encode/starlette/blob/master/CHANGELOG.md
- Audit baseline: `AI-TUTOR-AUDIT-CURRENT-2026-08-23.md` (4 known risks).
