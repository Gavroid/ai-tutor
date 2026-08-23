"""Evidence store for subject readiness.

Sprint 2026-08-22: единая точка истины для готовности предмета.

Evidence gates (все bool):
- manifest_ready       — checksum, source_url, license_decision, OCR status, known problem pages.
- mapping_ready        — topic/page mapping покрывает route topics с confidence=reviewed.
- import_ready         — local/staging import прошёл metadata audit.
- rag_ready            — retrieval probes проходят по subject/topic/page.
- practice_ready       — practice seeds с явным subject/topic, не generic fallback.
- manual_smoke_ready   — Explain/Practice/wrong→corrected/Chat/Clear/mobile QA пройдены.

Promotion gates:
- pilot_visible        — может быть показан ребёнку.
- promotion_allowed    — все evidence_ready=true, никаких blocked_ocr/not_available.

mvp_status (для обратной совместимости с frontend) — fail-closed:
- mvp_ready            — только если все evidence gates закрыты и promotion_allowed.
- internal_mvp         — есть seed/route, но не pilot.
- preview              — навигация, не pilot.
- blocked_ocr          — есть mapping, но OCR/caption/formula QA не закрыта.
- not_available        — источник или mapping отсутствует.

Источник evidence:
1. Если существует data/textbooks/7-class/evidence.json — читаем его.
2. Иначе используем встроенную policy map (на данный момент только math=ready).

Файл evidence.json должен иметь структуру:
{
  "math": {
    "manifest_ready": true,
    "mapping_ready": true,
    "import_ready": true,
    "rag_ready": true,
    "practice_ready": true,
    "manual_smoke_ready": true,
    "pilot_visible": true,
    "promotion_allowed": true,
    "blocked_reason": null
  },
  "algebra": { ... },
  ...
}
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


# Default evidence policy: только math имеет pilot_visible на этом этапе.
# Остальные предметы — preview, до явного evidence update через pipeline.
_DEFAULT_EVIDENCE: dict[str, dict[str, object]] = {
    "math": {
        "manifest_ready": True,
        "mapping_ready": True,
        "import_ready": True,
        "rag_ready": True,
        "practice_ready": True,
        "manual_smoke_ready": True,
        "pilot_visible": True,
        "promotion_allowed": True,
        "blocked_reason": None,
    },
}

# Subjects, для которых сейчас известны OCR/formula/caption проблемы —
# даже при готовом манифесте даём blocked_ocr до явной visual QA.
_KNOWN_OCR_BLOCKED: set[str] = {
    # 04 История (Россия): много репродукций и подписей.
    "hist",
    # 05 Всеобщая история: репродукции + mixed language OCR.
    "hist-world",
    # 11 Информатика: code blocks, таблицы.
    "inf",
    # 12 Обществознание: terms/tables OCR.
    "soc",
    # 13 Химия: формулы/таблицы, page 137.
    "chem",
    # 15 География: maps around 245-254.
    "geo",
}


_PILOT_SCOPE: set[str] = {"math"}


@dataclass(frozen=True)
class SubjectEvidence:
    """Evidence bag для одного предмета."""

    code: str
    manifest_ready: bool = False
    mapping_ready: bool = False
    import_ready: bool = False
    rag_ready: bool = False
    practice_ready: bool = False
    manual_smoke_ready: bool = False
    pilot_visible: bool = False
    promotion_allowed: bool = False
    blocked_reason: str | None = None

    def mvp_status(self) -> str:
        """Compute mvp_status fail-closed из evidence."""
        if self.promotion_allowed and all(
            [
                self.manifest_ready,
                self.mapping_ready,
                self.import_ready,
                self.rag_ready,
                self.practice_ready,
                self.manual_smoke_ready,
            ]
        ):
            return "mvp_ready"
        if self.blocked_reason:
            return self.blocked_reason  # blocked_ocr / not_available
        if any(
            [
                self.manifest_ready,
                self.mapping_ready,
                self.import_ready,
                self.rag_ready,
                self.practice_ready,
            ]
        ):
            return "internal_mvp"
        return "preview"

    def support_note(self) -> str:
        """Человекочитаемое объяснение текущего статуса для ребёнка/учителя."""
        status = self.mvp_status()
        if status == "mvp_ready":
            return (
                "Готово: маршрут, источники, практика и ручной smoke закрыты. "
                "Доступно пилоту."
            )
        if status == "internal_mvp":
            missing = []
            if not self.manifest_ready:
                missing.append("манифест учебника")
            if not self.mapping_ready:
                missing.append("topic/page mapping")
            if not self.import_ready:
                missing.append("импорт")
            if not self.rag_ready:
                missing.append("retrieval probes")
            if not self.practice_ready:
                missing.append("practice seeds")
            if not self.manual_smoke_ready:
                missing.append("ручной smoke")
            if not self.promotion_allowed:
                missing.append("promotion gate")
            return "В обработке: не закрыты " + ", ".join(missing) + "."
        if status == "blocked_ocr":
            return (
                "Заблокировано: OCR/формулы/карты/таблицы не прошли visual QA. "
                "Доступно только оператору."
            )
        if status == "not_available":
            return "Недоступно: источник или mapping не найден."
        return (
            "Preview: учебный маршрут виден, но материалы/RAG ещё не подтверждены. "
            "Используй для навигации, не для пилотного теста."
        )


def _default_for_code(code: str) -> SubjectEvidence:
    if code in _DEFAULT_EVIDENCE:
        row = _DEFAULT_EVIDENCE[code]
        return SubjectEvidence(code=code, **row)
    # Базовый fail-closed: ничего не готово, OCR-blocked если входит в список.
    blocked: str | None = None
    if code in _KNOWN_OCR_BLOCKED:
        blocked = "blocked_ocr"
    return SubjectEvidence(code=code, blocked_reason=blocked)


def _try_load_evidence_json() -> dict[str, SubjectEvidence] | None:
    """Попытаться загрузить evidence из data/textbooks/7-class/evidence.json.

    Ищем от корня backend-апп и от корня репозитория. Не падаем, если файла нет —
    значит evidence пока живёт только в policy map.
    """
    candidates: list[Path] = []
    here = Path(__file__).resolve()
    # В Docker-окружении: /app/app/subjects/evidence.py → here.parents[1] = /app/app,
    # here.parents[2] = /app. Здесь /opt/ai-tutor монтируется в /app или подобный путь.
    # На prod файл лежит в /opt/ai-tutor/data/textbooks/7-class/evidence.json.
    # На local dev: /root/workspace/ai-tutor/data/textbooks/7-class/evidence.json
    # или относительно here (через .parents[3] для backend layout).
    for up in [
        Path("/opt/ai-tutor"),  # production
        Path("/app"),  # standard docker
        Path("/root/workspace/ai-tutor"),  # local dev
        here.parents[3] if len(here.parents) >= 4 else here.parents[-1],  # dynamic
    ]:
        if not up:
            continue
        # PermissionError safe: внутри Docker-контейнера некоторые пути могут
        # быть недоступны. .exists() вызывает os.stat() и может бросить PermissionError.
        try:
            if up.exists():
                candidates.append(up / "data" / "textbooks" / "7-class" / "evidence.json")
        except (OSError, PermissionError):
            continue
    for path in candidates:
        try:
            if not path.exists():
                continue
        except (OSError, PermissionError):
            continue
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            out: dict[str, SubjectEvidence] = {}
            for code, row in raw.items():
                out[code] = SubjectEvidence(
                    code=code,
                    manifest_ready=bool(row.get("manifest_ready", False)),
                    mapping_ready=bool(row.get("mapping_ready", False)),
                    import_ready=bool(row.get("import_ready", False)),
                    rag_ready=bool(row.get("rag_ready", False)),
                    practice_ready=bool(row.get("practice_ready", False)),
                    manual_smoke_ready=bool(row.get("manual_smoke_ready", False)),
                    pilot_visible=bool(row.get("pilot_visible", False)),
                    promotion_allowed=bool(row.get("promotion_allowed", False)),
                    blocked_reason=row.get("blocked_reason"),
                )
            logger.info("Loaded subject evidence from %s (%d subjects)", path, len(out))
            return out
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to parse %s: %s", path, exc)
    return None


# Lazy-loaded cache: один раз прочитали evidence.json и закешировали.
_evidence_cache: dict[str, SubjectEvidence] | None = None
_evidence_loader = None


def get_evidence_for(code: str) -> SubjectEvidence:
    """Получить evidence для предмета.

    Приоритет:
    1. evidence.json, если он существует;
    2. встроенная policy map (_DEFAULT_EVIDENCE + _KNOWN_OCR_BLOCKED).
    """
    global _evidence_cache, _evidence_loader
    # Tests may temporarily replace the loader. Do not reuse a cache produced
    # by a different loader, otherwise monkeypatch teardown leaks evidence
    # state into the next test.
    current_loader = _try_load_evidence_json
    if _evidence_cache is None or _evidence_loader is not current_loader:
        loaded = current_loader()
        if loaded:
            _evidence_cache = loaded
        else:
            _evidence_cache = {}
        _evidence_loader = current_loader
    if code in _evidence_cache:
        return _evidence_cache[code]
    return _default_for_code(code)


def reset_evidence_cache() -> None:
    """Сбросить кеш (используется в тестах при подмене evidence.json)."""
    global _evidence_cache, _evidence_loader
    _evidence_cache = None
    _evidence_loader = None


def all_known_codes() -> list[str]:
    """Все коды, для которых у нас есть evidence (для диагностики)."""
    base = set(_DEFAULT_EVIDENCE.keys()) | _KNOWN_OCR_BLOCKED
    if _evidence_cache is None:
        loaded = _try_load_evidence_json()
        if loaded:
            base |= set(loaded.keys())
    return sorted(base)


def evidence_to_dict(ev: SubjectEvidence) -> dict[str, object]:
    """Преобразовать evidence в dict для API output."""
    return {
        "manifest_ready": ev.manifest_ready,
        "mapping_ready": ev.mapping_ready,
        "import_ready": ev.import_ready,
        "rag_ready": ev.rag_ready,
        "practice_ready": ev.practice_ready,
        "manual_smoke_ready": ev.manual_smoke_ready,
        "pilot_visible": ev.pilot_visible,
        "promotion_allowed": ev.promotion_allowed,
        "blocked_reason": ev.blocked_reason,
    }