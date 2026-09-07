"""Sprint 4 RAG production: auto-detect subject из filename + content keywords.

Стратегия (от простой к сложной):
1. Filename regex: `(?P<code>math|russian|physics|...)[_-]?(?P<grade>\\d+)?`
   → Subject.code lookup (если существует в БД).
2. Content keyword fallback (если есть content_preview):
   "уравнение" → math, " indefinite" → english, и т.д.
3. None (admin должен выбрать вручную в UI).

Не пытаемся быть умными: confidence < 0.7 → admin override в форме.
"""

from __future__ import annotations

import re
from typing import Final

from app.admin.rag_schemas import SubjectDetection

# Sprint 4 RAG: supported subject codes (must match Subject.code в БД).
# Не пытаемся покрыть всё — добавляем по мере необходимости.
_SUBJECT_PATTERNS: Final[dict[str, str]] = {
    "math": "math",
    "mathematics": "math",
    "алгебра": "math",
    "геометрия": "math",
    "russian": "russian",
    "русский": "russian",
    "physics": "physics",
    "физика": "physics",
    "chemistry": "chemistry",
    "химия": "chemistry",
    "biology": "biology",
    "биология": "biology",
    "history": "history",
    "история": "history",
    "english": "english",
    "английский": "english",
    "informatics": "informatics",
    "информатика": "informatics",
}

# Filename regex: code идёт от начала строки, grade — опциональная цифра после code или в конце.
# Примеры:
#   "math_7_class" → code="math", grade="7"
#   "russian-grammar-5" → code="russian", grade="5"
#   "mathematics.pdf" → code="mathematics" (→ math в SUBJECT_PATTERNS)
_FILENAME_RE: Final[re.Pattern[str]] = re.compile(
    r"^(?P<code>[a-zA-Zа-яА-ЯёЁ]+)(?:[_-](?P<grade_after>\d{1,2}))?",
    re.IGNORECASE,
)
# Grade может быть где угодно в имени файла (после code), например "russian-grammar-5".
_GRADE_FALLBACK_RE: Final[re.Pattern[str]] = re.compile(
    r"[_-](\d{1,2})(?:\.pdf)?$",
    re.IGNORECASE,
)

# Sprint 4 RAG: keyword → subject_code для content fallback.
# Keywords должны быть достаточно специфичны чтобы не давать false positives.
_KEYWORD_MAP: Final[dict[str, str]] = {
    "уравнение": "math",
    "интеграл": "math",
    "производная": "math",
    "треугольник": "math",
    "диктант": "russian",
    "морфологический": "russian",
    "синоним": "russian",
    "электричество": "physics",
    "магнитное поле": "physics",
    "кислота": "chemistry",
    "реакция": "chemistry",
    "клетка": "biology",
    "митоз": "biology",
    "революция": "history",
    "война": "history",
    "indefinite": "english",
    "past simple": "english",
}


def detect_subject_from_filename(
    filename: str,
    content_preview: str | None = None,
) -> SubjectDetection:
    """Sprint 4 RAG: auto-detect subject code из filename + content.

    Args:
        filename: имя PDF файла (например "math_7_class_quadratic_equations.pdf").
        content_preview: опционально первые N символов extracted text для keyword fallback.

    Returns:
        SubjectDetection с subject_code, grade, confidence, method.
        Если ничего не найдено — subject_code=None, admin override в UI.
    """
    # Stage 1: filename regex match.
    fname = filename.lower().replace(".pdf", "").strip()
    m = _FILENAME_RE.search(fname)
    if m:
        code_raw = m.group("code").lower() if m.group("code") else ""
        grade_str = m.group("grade_after") if m.group("grade_after") else None

        # Normalize к known subject code.
        subject_code = _SUBJECT_PATTERNS.get(code_raw)
        if subject_code:
            # Если grade не сразу за code, ищем в остатке имени.
            if grade_str is None:
                tail = fname[m.end() :]
                m2 = _GRADE_FALLBACK_RE.search(tail)
                if m2:
                    grade_str = m2.group(1)
            return SubjectDetection(
                subject_code=subject_code,
                grade=int(grade_str) if grade_str and grade_str.isdigit() else None,
                confidence=0.85,
                method="filename_regex",
            )

    # Stage 2: content keyword fallback (если есть preview).
    if content_preview:
        preview_lower = content_preview.lower()
        for keyword, subj_code in _KEYWORD_MAP.items():
            if keyword in preview_lower:
                return SubjectDetection(
                    subject_code=subj_code,
                    grade=None,
                    confidence=0.65,
                    method="keyword",
                )

    # Stage 3: ничего не нашли.
    return SubjectDetection(
        subject_code=None,
        grade=None,
        confidence=0.0,
        method="none",
    )
