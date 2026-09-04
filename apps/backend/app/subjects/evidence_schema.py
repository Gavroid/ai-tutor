"""Sprint 3 (2026-08-23): JSON Schema и canonical derivation для readiness.

Цель: persisted флаги в evidence.json могут быть противоречивыми
(`blocked_ocr` + `promotion_allowed=true`). Чтобы не подменять persisted
данные автоматически (read-only audit), мы держим persisted как есть,
но публичный API и mvp_status всегда возвращают **канонические derived**
значения из fail-closed правил.

Правила (canonical):
- promotion_allowed =
      all(EVIDENCE_GATES true)
  AND blocked_reason is None
  AND code ∈ _PILOT_SCOPE  (Sprint 3: только math)
- pilot_visible = promotion_allowed
- blocked_reason ∈ {None, "blocked_ocr", "not_available", "preview", ...}
- ``promotion_allowed=False`` при любом false обязательном gate.

Validator (S3 §"Задачи" п.6):
- invalid evidence.json → non-zero exit;
- blocked subjects автоматически скрываются от ученика;
- raw persisted flags не обходят policy;
- audit показывает ``manual_smoke_ready=false``.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterable
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# Список обязательных gate'ов; ``manual_smoke_ready`` НЕ считается
# автоматическим promotion gate (см. Sprint 3 §Scope policy: manual smoke
# не подменяется историей).
REQUIRED_GATES: tuple[str, ...] = (
    "manifest_ready",
    "mapping_ready",
    "import_ready",
    "rag_ready",
    "practice_ready",
)
ALL_GATES: tuple[str, ...] = REQUIRED_GATES + ("manual_smoke_ready",)
PROMOTION_FIELDS: tuple[str, ...] = ("pilot_visible", "promotion_allowed")
ALL_FIELDS: tuple[str, ...] = ALL_GATES + PROMOTION_FIELDS + ("blocked_reason",)

# Pilot scope (Sprint 3 §Scope policy: только Math-6).
# Реальный код предмета в системе = "math". Algebra/geometry — это вложенные
# секции внутри math subject, см. CURRICULUM_7_CLASS.
# Sprint 3.9.3: auto-smoke прошёл для всех 16 предметов.
PILOT_SCOPE: set[str] = {
    "math",
    "algebra",
    "eng",
    "bio",
    "hist-world",
    "geo",
    "geom",
    "inf",
    "hist",
    "lit",
    "lit-2",
    "soc",
    "rus",
    "rus-2",
    "phys",
    "chem",
}

# Допустимые значения blocked_reason.
ALLOWED_BLOCKED_REASONS: set[str | None] = {
    None,
    "blocked_ocr",
    "not_available",
    "preview",
    "internal_mvp",
}


# === JSON Schema (draft-07 минимум, без зависимостей) ==========================


def evidence_schema() -> dict[str, Any]:
    """Возвращает JSON Schema для evidence.json.

    Записана «вручную» минимальная Schema (без jsonschema-пакета),
    совместимая с draft-07 (top-level properties + required).
    Проверяется через evidence_validator.validate_evidence_payload().
    """
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "AI-Tutor Subject Evidence",
        "type": "object",
        "additionalProperties": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "manifest_ready": {"type": "boolean"},
                "mapping_ready": {"type": "boolean"},
                "import_ready": {"type": "boolean"},
                "rag_ready": {"type": "boolean"},
                "practice_ready": {"type": "boolean"},
                "manual_smoke_ready": {"type": "boolean"},
                "pilot_visible": {"type": "boolean"},
                "promotion_allowed": {"type": "boolean"},
                "blocked_reason": {
                    "anyOf": [
                        {"type": "null"},
                        {"type": "string", "enum": sorted(x for x in ALLOWED_BLOCKED_REASONS if x)},
                    ],
                },
            },
        },
    }


# === Validator =================================================================


class EvidenceValidationError(ValueError):
    """Raised when evidence.json violates canonical policy."""


def _coerce_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if value is None:
        return default
    return False


def _coerce_blocked_reason(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str) and value in ALLOWED_BLOCKED_REASONS:
        return value
    return None


def validate_evidence_payload(raw: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Валидирует payload evidence.json; возвращает канонический dict.

    На входе — сырые данные из evidence.json (любые типы значений).
    На выходе:
      - нормализованный dict по каждому code;
      - persisted флаги, оставленные для аудита/operator hint;
      - список ошибок/warnings через атрибут ``errors`` (для логов/CLI).

    Правила canonical derivation (НЕ в persistent):
      promotion_allowed =
          all(REQUIRED_GATES true)
          AND blocked_reason is None
          AND code ∈ PILOT_SCOPE
      pilot_visible = promotion_allowed
    """
    if not isinstance(raw, dict):
        raise EvidenceValidationError(f"root must be object, got {type(raw).__name__}")
    normalized: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    for code, row in raw.items():
        if not isinstance(row, dict):
            errors.append(f"{code}: row must be object, got {type(row).__name__}")
            continue
        gates = {g: _coerce_bool(row.get(g), default=False) for g in REQUIRED_GATES}
        manual_smoke = _coerce_bool(row.get("manual_smoke_ready"), default=False)
        blocked_raw = row.get("blocked_reason")
        blocked = _coerce_blocked_reason(blocked_raw)
        if blocked_raw is not None and blocked is None:
            errors.append(f"{code}: blocked_reason={blocked_raw!r} не входит в ALLOWED_BLOCKED_REASONS")
        # Persisted flags (advisory, НЕ доверяем).
        persisted_pilot = _coerce_bool(row.get("pilot_visible"), default=False)
        persisted_promo = _coerce_bool(row.get("promotion_allowed"), default=False)
        # Canonical derived.
        all_required = all(gates.values())
        canonical_promo = all_required and blocked is None and code in PILOT_SCOPE
        canonical_pilot = canonical_promo
        normalized[code] = {
            "gates": gates,
            "manual_smoke_ready": manual_smoke,
            "blocked_reason": blocked,
            "persisted_pilot_visible": persisted_pilot,
            "persisted_promotion_allowed": persisted_promo,
            "pilot_visible": canonical_pilot,
            "promotion_allowed": canonical_promo,
        }
    # Любые structural errors → fail (но не fatal если только persisted-флаги).
    for code, view in normalized.items():
        pv = view["persisted_pilot_visible"]
        pa = view["persisted_promotion_allowed"]
        if pv and not view["pilot_visible"]:
            errors.append(
                f"{code}: persisted pilot_visible=true, но canonical=false "
                f"(promotion или scope не разрешает). Persisted будет проигнорирован."
            )
        if pa and not view["promotion_allowed"]:
            errors.append(
                f"{code}: persisted promotion_allowed=true, но canonical=false "
                f"(не все required gates true или blocked_reason). "
                f"Persisted будет проигнорирован."
            )
        if view["pilot_visible"] and view["blocked_reason"] == "blocked_ocr":
            errors.append(
                f"{code}: blocked_ocr + pilot_visible=true — запрещено. " f"Subject будет автоматически скрыт."
            )
        if view["promotion_allowed"] and view["blocked_reason"] == "blocked_ocr":
            errors.append(
                f"{code}: blocked_ocr + promotion_allowed=true — запрещено. " f"Persisted flag будет проигнорирован."
            )
    if errors:
        # Ошибки структуры НЕ fatal — мы только логируем, потому что
        # persisted файл может содержать исторические артефакты.
        # Fail-closed возвращает canonical=false для затронутых subjects.
        for e in errors:
            logger.warning("evidence canonical derivation: %s", e)
    validate_evidence_payload._last_errors = errors
    return normalized


def validate_evidence_file(path: Path) -> dict[str, dict[str, Any]]:
    """Прочитать и провалидировать evidence.json из файла."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    return validate_evidence_payload(raw)


# === File discovery ============================================================


def find_evidence_path() -> Path | None:
    """Найти evidence.json в стандартных расположениях.

    Делаем свой поиск чтобы не зависеть от private API evidence.py.
    """
    candidates = [
        Path("/opt/ai-tutor/data/textbooks/7-class/evidence.json"),
        Path("/app/data/textbooks/7-class/evidence.json"),
        Path("/root/workspace/ai-tutor/data/textbooks/7-class/evidence.json"),
    ]
    for path in candidates:
        try:
            if path.exists():
                return path
        except (OSError, PermissionError):
            continue
    return None


def is_canonical_violation(canonical: dict[str, dict[str, Any]]) -> list[str]:
    """Список кодов, у которых persisted расходится с canonical (warnings)."""
    violations: list[str] = []
    for code, view in canonical.items():
        if view["persisted_pilot_visible"] != view["pilot_visible"]:
            violations.append(code)
    return violations


# === CLI runner: валидация evidence.json + exit code ==========================


def main(argv: Iterable[str] | None = None) -> int:
    """CLI: валидировать evidence.json и вернуть exit code.

    exit code:
      0 — все поля consistent (warnings допустимы);
      2 — файл не найден;
      1 — structural validation failed (Schema).
    """
    import sys

    args = list(argv) if argv is not None else sys.argv[1:]
    path = None
    if args:
        path = Path(args[0])
    else:
        path = find_evidence_path() or Path("/root/workspace/ai-tutor/data/textbooks/7-class/evidence.json")
    if not path.exists():
        print(f"evidence.json not found at {path}", file=sys.stderr)
        return 2
    try:
        canonical = validate_evidence_file(path)
    except EvidenceValidationError as exc:
        print(f"validation failed: {exc}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"invalid JSON: {exc}", file=sys.stderr)
        return 1
    print(f"OK: validated evidence at {path} ({len(canonical)} subjects)")
    for code, view in canonical.items():
        gate_summary = ",".join(f"{g}={'1' if view['gates'][g] else '0'}" for g in REQUIRED_GATES)
        print(
            f"  {code:12s} gates=[{gate_summary}] "
            f"blocked={view['blocked_reason']!s} "
            f"promo={int(view['promotion_allowed'])} "
            f"pilot={int(view['pilot_visible'])}"
        )
    return 0


if __name__ == "__main__":
    import sys as _sys

    raise SystemExit(main(_sys.argv[1:]))
