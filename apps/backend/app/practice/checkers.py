"""Sprint 8.2 — чекеры для автопроверки практических задач.

3 стратегии:
- numeric — ответ сравнивается с эталоном как число (с допуском).
- keyword — в ответе должны присутствовать ключевые слова (case-insensitive, min-match-score).
- semantic — для неоднозначных случаев: AI-judge через /ai/check-answer.

Использование:
    from app.practice.checkers import check_answer
    result = check_answer(
        user_answer="42",
        ref_solution="42",
        checker_type="numeric",
        keywords=["ответ"],
        question_text="Сколько будет 6*7?"
    )
    if result["correct"]: ...

Sprint 8.2: эталонные решения уже есть в PracticeTask.reference_solution.
"""
from __future__ import annotations

import re
from typing import Literal

CheckerType = Literal["numeric", "keyword", "semantic", "exact"]

# Допуск для numeric сравнения (абсолютная разница или процент)
NUMERIC_ABS_TOLERANCE = 0.01
NUMERIC_REL_TOLERANCE = 0.01  # 1%


def _normalize(s: str) -> str:
    """Нормализация текста: lowercase + trim + убрать лишние пробелы."""
    return re.sub(r"\s+", " ", s.strip().lower())


def check_numeric(user: str, ref: str) -> bool:
    """Numeric: точное число или с допуском.

    Поддерживает «42», «42.0», «42.5» — парсится через regex.
    Допуск: или NUMERIC_ABS_TOLERANCE абсолютная разница,
            или NUMERIC_REL_TOLERANCE процент (от max(|ref|, 1)).
    """
    # Извлекаем первое число из строки (убираем единицы измерения)
    user_num = _extract_number(user)
    ref_num = _extract_number(ref)

    if user_num is None or ref_num is None:
        return False

    diff = abs(user_num - ref_num)
    if diff <= NUMERIC_ABS_TOLERANCE:
        return True
    # Процентный допуск
    base = max(abs(ref_num), 1)
    return (diff / base) <= NUMERIC_REL_TOLERANCE


def _extract_number(s: str) -> float | None:
    """Извлечь первое число из строки."""
    s = s.replace(",", ".")
    # Ищем первое числовое представление
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    if m:
        try:
            return float(m.group())
        except ValueError:
            return None
    return None


def check_keyword(user: str, ref: str, required_keywords: list[str] | None = None) -> dict:
    """Keyword: проверяет наличие ключевых слов в ответе ученика.

    Args:
        user: ответ ученика.
        ref: эталонное решение (используется только для подсчёта "хороших" слов).
        required_keywords: список ключевых слов (если None — берём первые 3 слова эталона).

    Returns:
        {"correct": bool, "matched": [str], "missing": [str], "score": float 0..1}
    """
    user_norm = _normalize(user)

    if not required_keywords:
        # Берём первые 3 значимых слова (>2 символов) из ref
        words = re.findall(r"\b\w{3,}\b", ref.lower())
        required_keywords = words[:3] if len(words) >= 3 else words

    if not required_keywords:
        # Эталон пустой — считаем что ученик не может ответить правильно.
        return {"correct": False, "matched": [], "missing": [], "score": 0.0}

    matched = [k for k in required_keywords if _normalize(k) in user_norm]
    missing = [k for k in required_keywords if _normalize(k) not in user_norm]
    score = len(matched) / len(required_keywords) if required_keywords else 0.0
    # correct = все ключевые слова найдены
    return {
        "correct": len(missing) == 0,
        "matched": matched,
        "missing": missing,
        "score": score,
    }


def check_exact(user: str, ref: str) -> bool:
    """Exact: точное совпадение с нормализацией.

    Используется для коротких ответов типа «Да/Нет» или «True».
    """
    return _normalize(user) == _normalize(ref)


def check_answer(
    user_answer: str,
    reference_solution: str,
    checker_type: CheckerType | str = "keyword",
    keywords: list[str] | None = None,
    question_text: str = "",
) -> dict:
    """Универсальная проверка ответа ученика (Sprint 8.2).

    Args:
        user_answer: что ученик ввёл.
        reference_solution: эталон (сгенерирован AI).
        checker_type: numeric | keyword | semantic | exact.
        keywords: для keyword-чекера — какие слова обязательны.
        question_text: контекст для semantic judge.

    Returns:
        {
          "correct": bool,
          "score": float 0..1,
          "checker": str,
          "details": {...}
        }
    """
    user = (user_answer or "").strip()
    ref = (reference_solution or "").strip()

    if not user:
        return {
            "correct": False,
            "score": 0.0,
            "checker": checker_type,
            "details": {"reason": "empty answer"},
        }

    ct = (checker_type or "keyword").lower()

    if ct == "numeric":
        ok = check_numeric(user, ref)
        return {
            "correct": ok,
            "score": 1.0 if ok else 0.0,
            "checker": "numeric",
            "details": {"user": user, "ref": ref},
        }

    if ct == "exact":
        ok = check_exact(user, ref)
        return {
            "correct": ok,
            "score": 1.0 if ok else 0.0,
            "checker": "exact",
            "details": {"user": user, "ref": ref},
        }

    if ct == "keyword":
        kw = keywords or []
        result = check_keyword(user, ref, kw)
        return {
            "correct": result["correct"],
            "score": result["score"],
            "checker": "keyword",
            "details": {
                "matched": result["matched"],
                "missing": result["missing"],
                "user": user,
            },
        }

    if ct == "semantic":
        # AI-judge fallback: используем существующий /ai/check-answer через
        # прямое использование AIService. Но это async — мы не можем вызвать
        # напрямую из sync функции. Помечаем как нужно AI-judge.
        return {
            "correct": False,
            "score": 0.0,
            "checker": "semantic",
            "details": {
                "reason": "semantic checker requires async AI judge (not implemented in Sprint 8.2 sync API)",
                "user": user,
                "ref": ref,
            },
        }

    return {
        "correct": False,
        "score": 0.0,
        "checker": ct,
        "details": {"reason": f"unknown checker_type: {ct}"},
    }
