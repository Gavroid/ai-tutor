"""Sprint 3.28: вынесенные dataclasses QuizQuestion + Quiz из app.ai.service.

До Sprint 3.28: app/ai/service.py содержал 4 dataclass (CheckResult,
GeneratedExercise, QuizQuestion, Quiz). Sprint 3.28 step 1 — CheckResult
и GeneratedExercise → app.ai.datatypes. Этот файл — step 2: QuizQuestion/Quiz.
Они живут вместе потому что Quiz ссылается на list[QuizQuestion].

После Sprint 3.28: чистые dataclasses в этом файле. service.py re-export'ит
для backward compatibility.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class QuizQuestion:
    """Один вопрос квиза (режим mode='quiz').

    Поля совпадают со схемой, которую LLM возвращает в JSON.
    """

    question_text: str
    type: str  # "single" | "multiple" | "numeric" | "text"
    options: list[str] | None
    correct_answer: str
    explanation: str


@dataclass
class Quiz:
    """Набор вопросов, сгенерированных AI для квиза."""

    questions: list[QuizQuestion]
