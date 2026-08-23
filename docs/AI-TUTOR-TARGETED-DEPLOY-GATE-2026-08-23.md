# AI-Tutor — targeted deploy gate evidence

Дата: 2026-08-23
Режим: offline/read-only; SSH, deploy и production mutation не выполнялись.

## Изменение

`targeted_deploy_manifest.py` теперь возвращает для runtime changes:

```text
release_gate=math_only_scope_and_external_evidence_required
can_deploy=false
required_evidence:
  - scope_snapshot
  - backup_offsite
  - restore_drill
  - student_smoke
```

Docs-only changes остаются без deploy gate:

```text
release_gate=docs_only
can_deploy=true
```

## Проверки

```text
Targeted deploy tests: 7 passed
Scope drift + deploy tests: 9 passed
Runtime CLI manifest: exit 2
Docs-only CLI manifest: exit 0
Python compile: passed
git diff --check: passed
```

Runtime deploy намеренно заблокирован до подтверждения Math-only production scope и внешних operational gates.
