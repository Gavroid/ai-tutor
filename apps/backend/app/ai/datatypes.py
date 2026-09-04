"""Sprint 3.28: выделенные dataclasses из app.ai.service.

До Sprint 3.28: app/ai/service.py содержал 4 dataclass (CheckResult,
GeneratedExercise, QuizQuestion, Quiz) inline. Это делало файл god-like (1560 LOC)
без реальной причины — dataclasses не зависят от других модулей и могут жить
отдельно.

После Sprint 3.28: чистые dataclasses в этом файле. service.py re-export'ит
для backward compatibility (до Sprint 3.29+).

Re-exports сохраняются:
    from app.ai.datatypes import CheckResult, GeneratedExercise  # новый путь
    from app.ai.service import CheckResult, GeneratedExercise    # legacy путь

Не содержат никакой бизнес-логики — только структура данных.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CheckResult:
    is_correct: bool
    score: float
    first_error: str | None
    explanation: str
    hint_level: int
    next_difficulty: int
    # Sprint 4.3.1: тип ошибки для context-aware hints.
    # ARITHMETIC/CONCEPTUAL/LOGIC/CARELESS или None если ответ правильный.
    error_type: str | None = None


@dataclass
class GeneratedExercise:
    question_text: str
    type: str
    options: list[str] | None
    correct_answer: str
    explanation: str
    typical_mistakes: list[str]
