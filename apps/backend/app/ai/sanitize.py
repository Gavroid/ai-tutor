"""Sanitization входа и выхода LLM: защита от prompt injection и утечек.

Минимальная, но рабочая:
- Ограничение длины входа
- Удаление управляющих символов (кроме \\n, \\t)
- Удаление markdown-инъекций (```system, [INST] и т.д.)
- Очистка HTML в финальном ответе
"""
from __future__ import annotations

import html
import re
from typing import Final

# Символы, которые могут попытаться «сломать» системный промпт
_INJECTION_PATTERNS: Final[re.RegexPattern[str]] = re.compile(
    r"(?im)(\bignore (all )?previous instructions?\b|"
    r"\bforget (everything|all)\b|"
    r"\bdisregard (the )?(system|above)\b|"
    r"\byou are now\b|"
    r"\[INST\]|"
    r"<\|system\|>|"
    r"```system|"
    r"###\s*system\s*###|"
    r"\bact as\b.*\bno restrictions?\b)"
)


def sanitize_user_input(text: str, max_chars: int) -> str:
    """Очистить пользовательский ввод перед подстановкой в LLM-промпт."""
    if not text:
        return ""
    text = text[:max_chars]
    text = text.replace("\x00", "")  # NULL
    # Удаляем прочие управляющие символы, кроме \t \n \r
    out: list[str] = []
    for ch in text:
        code = ord(ch)
        if code < 32 and ch not in ("\t", "\n", "\r"):
            continue
        if code == 127:  # DEL
            continue
        out.append(ch)
    return "".join(out).strip()


def detect_injection(text: str) -> bool:
    """Возвращает True, если в тексте найдены попытки prompt injection."""
    if not text:
        return False
    return bool(_INJECTION_PATTERNS.search(text))


def sanitize_output(text: str) -> str:
    """Очистить HTML в ответе LLM перед отдачей пользователю.

    Экранирует < > &, но сохраняет переносы строк.
    """
    if not text:
        return ""
    # Экранируем HTML
    text = html.escape(text, quote=True)
    return text.strip()