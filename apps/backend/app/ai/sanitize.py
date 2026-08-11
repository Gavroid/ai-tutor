"""Sanitization входа и выхода LLM: защита от prompt injection и утечек."""
from __future__ import annotations

import html
import re
from typing import Final

_LATEX_FRAC_RE: Final[re.Pattern[str]] = re.compile(r"\\frac\{([^{}]+)\}\{([^{}]+)\}")
_LATEX_TEXT_RE: Final[re.Pattern[str]] = re.compile(r"\\text\{([^{}]+)\}")
_DISPLAY_MATH_RE: Final[re.Pattern[str]] = re.compile(r"\$\$\s*(.*?)\s*\$\$", re.DOTALL)
_INLINE_MATH_RE: Final[re.Pattern[str]] = re.compile(r"(?<!\\)\$(?!\$)(.*?)(?<!\\)\$")
_ANGLE_ENTITY_RE: Final[re.Pattern[str]] = re.compile(r"^\s*&(?:amp;)?gt;\s*$")

# Символы, которые могут попытаться «сломать» системный промпт
_INJECTION_PATTERNS: Final[re.Pattern[str]] = re.compile(
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


def _normalize_latex(text: str) -> str:
    """Convert simple LaTeX fragments into readable student text."""
    text = _DISPLAY_MATH_RE.sub(lambda m: m.group(1).strip(), text)
    text = _INLINE_MATH_RE.sub(lambda m: m.group(1).strip(), text)
    text = text.replace("$$", "")
    text = _LATEX_TEXT_RE.sub(lambda m: m.group(1), text)
    # Common LLM/PDF artefact for decimal comma inside LaTeX groups: 110{,}6.
    text = text.replace("{,}", ",")
    for _ in range(3):
        text = _LATEX_FRAC_RE.sub(
            lambda m: f"{m.group(1).strip()} / {m.group(2).strip()}",
            text,
        )
    text = text.replace(r"\cdot", "×").replace(r"\times", "×")
    text = text.replace(r"\div", ":").replace(r"\:", ":")
    text = text.replace(r"\dots", "…").replace(r"\ldots", "…")
    text = re.sub(r"\b([A-Za-zА-Яа-я])_\{?([0-9A-Za-zА-Яа-я]+)\}?", r"\1\2", text)
    text = text.replace(r"\%", "%")
    return text


def _normalize_markdown_artifacts(text: str) -> str:
    """Remove visible markdown/HTML artefacts that confuse pupils."""
    lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if _ANGLE_ENTITY_RE.match(line):
            continue
        if _ANGLE_ENTITY_RE.match(html.unescape(line)):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


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
    """Normalize model output before frontend Markdown rendering.

    The frontend renderer already escapes HTML. Returning HTML-escaped text here
    caused double escaping like ``&amp;gt;`` and visible formula artefacts.
    """
    if not text:
        return ""
    text = html.unescape(text)
    text = _normalize_latex(text)
    text = _normalize_markdown_artifacts(text)
    return text.strip()
