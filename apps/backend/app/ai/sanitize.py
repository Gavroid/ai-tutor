"""Sanitization входа и выхода LLM: защита от prompt injection и утечек."""

from __future__ import annotations

import html
import re
from typing import Final

_LATEX_FRAC_RE: Final[re.Pattern[str]] = re.compile(r"\\frac\{([^{}]+)\}\{([^{}]+)\}")
_LATEX_TEXT_RE: Final[re.Pattern[str]] = re.compile(r"\\text\{([^{}]+)\}")
_LATEX_DISPLAY_PAREN_RE: Final[re.Pattern[str]] = re.compile(r"\\\[\s*(.*?)\s*\\\]", re.DOTALL)
_LATEX_INLINE_PAREN_RE: Final[re.Pattern[str]] = re.compile(r"\\\((.*?)\\\)")
_DISPLAY_MATH_RE: Final[re.Pattern[str]] = re.compile(r"\$\$\s*(.*?)\s*\$\$", re.DOTALL)
_INLINE_MATH_RE: Final[re.Pattern[str]] = re.compile(r"(?<!\\)\$(?!\\$)(.*?)(?<!\\)\$")
_ANGLE_ENTITY_RE: Final[re.Pattern[str]] = re.compile(r"^\s*&(?:amp;)?gt;\s*$")

# Sprint 3.9.1: GPT-5.6-luna часто генерирует LaTeX через \( ... \) и \[ ... \]
# (LaTeX-нотация), а не $...$ (Pandoc/MathJax). Раньше _normalize_latex их не ловил,
# и \\(50^\\circ\\) оставался в выводе как plain text. Теперь обрабатываем оба стиля.
# Также конвертируем часто используемые LaTeX-команды в Unicode/простой текст,
# чтобы Кирилл видел «∠B = 50°», а не «\\angle B = 50^{\\circ}».

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
    """Convert simple LaTeX fragments into readable student text.

    Sprint 3.9.1: расширил поддержку.
    - Ловит как `$...$`/`$$...$$` (Pandoc/MathJax), так и `\\(...\\)`/`\\[...\\]` (LaTeX-native).
    - Конвертирует распространённые команды в Unicode:
        \\angle → ∠, \\triangle → △, \\circ / ^\\circ → °
        \\leq → ≤, \\geq → ≥, \\neq → ≠, \\pm → ±
        \\cdot / \\times → ×, \\div → ÷, \\to → →
        \\sqrt{X} → √(X)
        \\overline{AB} → AB
        \\mathbf{X} → X
    - \\text{X} → X (просто текст)
    - \\frac{a}{b} → a / b
    - LaTeX-команды, которые не знаем — убираем обратный слэш, оставляем имя.
    """
    # 1) Display math \[ ... \] → раскрыть скобки, нормализовать содержимое.
    text = _LATEX_DISPLAY_PAREN_RE.sub(lambda m: _normalize_latex(m.group(1).strip()), text)
    # 2) Inline math \( ... \) → раскрыть скобки, нормализовать содержимое.
    text = _LATEX_INLINE_PAREN_RE.sub(lambda m: _normalize_latex(m.group(1).strip()), text)
    # 3) Display math $$ ... $$ и inline $...$ (как раньше).
    text = _DISPLAY_MATH_RE.sub(lambda m: m.group(1).strip(), text)
    text = _INLINE_MATH_RE.sub(lambda m: m.group(1).strip(), text)
    text = text.replace("$$", "")
    # 4) \text{X} → X
    text = _LATEX_TEXT_RE.sub(lambda m: m.group(1), text)
    # 5) Дробь \frac{a}{b} → a / b (3 итерации для вложенных).
    for _ in range(3):
        text = _LATEX_FRAC_RE.sub(
            lambda m: f"{m.group(1).strip()} / {m.group(2).strip()}",
            text,
        )
    # 6) Частые символы/операторы → Unicode.
    text = text.replace(r"\angle", "∠")
    text = text.replace(r"\triangle", "△")
    text = text.replace(r"\square", "□")
    text = text.replace(r"\cdot", "×").replace(r"\times", "×").replace(r"\div", "÷")
    text = text.replace(r"\pm", "±")
    text = text.replace(r"\leq", "≤").replace(r"\le ", "≤ ")
    text = text.replace(r"\geq", "≥").replace(r"\ge ", "≥ ")
    text = text.replace(r"\neq", "≠").replace(r"\ne ", "≠ ")
    text = text.replace(r"\approx", "≈")
    text = text.replace(r"\to", "→").replace(r"\rightarrow", "→")
    text = text.replace(r"\infty", "∞")
    text = text.replace(r"\cdot", "×")
    # 7) Степени: 50^\circ → 50°, x^{2} → x², x^2 → x², x^{10} → x¹⁰.
    text = _re_unicode_degrees(text)
    text = _re_unicode_superscripts(text)
    # 8) Индексы: x_{12} → x₁₂, x_1 → x₁, AB_1 → AB₁.
    text = _re_unicode_subscripts(text)
    # 9) Квадратный корень: \sqrt{X} → √(X), \sqrt[3]{X} → ∛(X).
    text = re.sub(r"\\sqrt\[([0-9]+)\]\{([^{}]+)\}", r"∛(\2)", text)
    text = re.sub(r"\\sqrt\{([^{}]+)\}", r"√(\1)", text)
    text = text.replace(r"\sqrt", "√")
    # 10) Декораторы: \overline{AB} → AB, \mathbf{X} → X, \mathrm{X} → X.
    text = re.sub(r"\\overline\{([^{}]+)\}", r"\1", text)
    text = re.sub(r"\\mathbf\{([^{}]+)\}", r"\1", text)
    text = re.sub(r"\\mathrm\{([^{}]+)\}", r"\1", text)
    text = re.sub(r"\\mathit\{([^{}]+)\}", r"\1", text)
    text = re.sub(r"\\hbox\{([^{}]+)\}", r"\1", text)
    # 11) L10n запятая в группах: {,} → ,
    text = text.replace("{,}", ",")
    # 12) Любая оставшаяся \command → command (без бэкслэша).
    text = re.sub(r"\\([a-zA-Z]+)", r"\1", text)
    # 13) Одиночные оставшиеся \{ и \} → ( ).
    text = text.replace("\\{", "(").replace("\\}", ")")
    # 14) Экранированные символы \% → %, \& → &, \$ → $.
    text = text.replace(r"\%", "%").replace(r"\&", "&").replace(r"\$", "$")
    # 15) Подчёркивание в identifiers (часто приходит a_1, AB_2).
    text = re.sub(r"\b([A-Za-zА-Яа-я])_\{?([0-9A-Za-zА-Яа-я]+)\}?", r"\1\2", text)
    return text


# === Unicode helpers для степеней, индексов, градусов ===

_SUPERSCRIPT_MAP = {
    "0": "⁰",
    "1": "¹",
    "2": "²",
    "3": "³",
    "4": "⁴",
    "5": "⁵",
    "6": "⁶",
    "7": "⁷",
    "8": "⁸",
    "9": "⁹",
    "+": "⁺",
    "-": "⁻",
    "=": "⁼",
    "(": "⁽",
    ")": "⁾",
    "n": "ⁿ",
    "i": "ⁱ",
}
_SUBSCRIPT_MAP = {
    "0": "₀",
    "1": "₁",
    "2": "₂",
    "3": "₃",
    "4": "₄",
    "5": "₅",
    "6": "₆",
    "7": "₇",
    "8": "₈",
    "9": "₉",
    "+": "₊",
    "-": "₋",
    "=": "₌",
    "(": "₍",
    ")": "₎",
    # LaTeX-команды для специальных subscript-символов (редко, но встречаются).
    "i": "ᵢ",
    "j": "ⱼ",
    "k": "ₖ",
    "n": "ₙ",
    "m": "ₘ",
    "p": "ₚ",
    "r": "ᵣ",
    "s": "ₛ",
    "t": "ₜ",
    "u": "ᵤ",
    "v": "ᵥ",
    "x": "ₓ",
}


def _re_unicode_degrees(text: str) -> str:
    """50^\\circ → 50°, 50^{\\circ} → 50°, x^{\\circ} → x°."""
    text = re.sub(r"\^\s*\\circ\b", "°", text)
    text = re.sub(r"\^\s*\{\s*\\circ\s*\}", "°", text)
    # Plain ^circ без бэкслэша (после шага 12 \circ → circ, останется "^circ")
    text = re.sub(r"\^\s*circ\b", "°", text)
    return text


def _re_unicode_superscripts(text: str) -> str:
    """x^2 → x², x^{10} → x¹⁰, x^{n+1} → xⁿ⁺¹, x^10 → x¹⁰."""

    def repl_brace(m: re.Match[str]) -> str:
        inner = m.group(1)
        return "".join(_SUPERSCRIPT_MAP.get(c, c) for c in inner)

    text = re.sub(r"\^\{([^{}]+)\}", repl_brace, text)
    # Greedy: x^10 → x¹⁰. Захватываем максимально длинную последовательность
    # символов из маппинга (цифры, буквы i/n, +/-/=/ и скобки).
    _SUPER_CHARS = set(_SUPERSCRIPT_MAP.keys())
    # Триггер: одиночный ^ в начале math-выражения. Срабатывает на любом ^.
    # Идём по тексту и для каждого ^ поглощаем последующие символы.
    out: list[str] = []
    i = 0
    while i < len(text):
        if text[i] == "^":
            j = i + 1
            consumed: list[str] = []
            while j < len(text) and text[j] in _SUPER_CHARS:
                consumed.append(text[j])
                j += 1
            if consumed:
                out.append("".join(_SUPERSCRIPT_MAP.get(c, c) for c in consumed))
                i = j
                continue
        out.append(text[i])
        i += 1
    text = "".join(out)
    return text


def _re_unicode_subscripts(text: str) -> str:
    """x_{12} → x₁₂, x_1 → x₁, AB_{10} → AB₁₀, x_{n+1} → xₙ₊₁."""

    def repl_brace(m: re.Match[str]) -> str:
        inner = m.group(1)
        return "".join(_SUBSCRIPT_MAP.get(c, c) for c in inner)

    text = re.sub(r"_\{([^{}]+)\}", repl_brace, text)
    # Greedy: x_12 → x₁₂.
    _SUB_CHARS = set(_SUBSCRIPT_MAP.keys())
    out: list[str] = []
    i = 0
    while i < len(text):
        if text[i] == "_":
            j = i + 1
            consumed: list[str] = []
            while j < len(text) and text[j] in _SUB_CHARS:
                consumed.append(text[j])
                j += 1
            if consumed:
                out.append("".join(_SUBSCRIPT_MAP.get(c, c) for c in consumed))
                i = j
                continue
        out.append(text[i])
        i += 1
    text = "".join(out)
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
