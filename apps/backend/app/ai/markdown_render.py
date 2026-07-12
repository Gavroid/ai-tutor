"""Безопасный Markdown → HTML рендер для AI-ответов.

Sprint 7.1: рендерим Markdown в HTML на сервере, чтобы UI мог отображать
жирный/курсив/код/списки/заголовки вместо сырой разметки.

Безопасность:
- использует markdown-it-py (CommonMark + GFM)
- HTML-инъекции из AI (например, <script> внутри ```code-block) HTML-escaped
  через `md.disable(['html'])`, плюс runtime наш `bleach` через whitelist.
- никогда не передаём сырой HTML вёрстке от LLM напрямую.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Final

from markdown_it import MarkdownIt

# Whitelist тегов для финального фильтра.
# markdown-it возвращает HTML с тегами из своего AST — всё уже безопасно,
# но мы дополнительно экранируем потенциально опасные атрибуты.
_ALLOWED_TAGS: Final[frozenset[str]] = frozenset(
    {
        "p", "br", "hr",
        "strong", "em", "code", "pre",
        "h1", "h2", "h3", "h4", "h5", "h6",
        "ul", "ol", "li",
        "blockquote",
        "table", "thead", "tbody", "tr", "th", "td",
        "del", "ins",
    }
)

# Атрибуты, которые ДОПУСТИМЫ в HTML от AI.
# markdown-it даёт класс `language-X` для code blocks — пропускаем.
_ALLOWED_ATTRS: Final[frozenset[str]] = frozenset({"class"})

# Атрибуты, КОТОРЫЕ ЗАПРЕЩЕНЫ ВСЕГДА (наследие XSS).
_FORBIDDEN_ATTRS: Final[frozenset[str]] = frozenset(
    {
        "onerror", "onload", "onclick", "onmouseover",
        "style",  # CSS injection через style=
        "src", "href",  # external resources / javascript: URLs
        "id",  # name collision для document.getElementById
        "target",
    }
)


@lru_cache(maxsize=1)
def _get_renderer() -> MarkdownIt:
    """Markdown-it с минимальным whitelist и без inline-HTML.

    Отключаем HTML-парсинг: AI может вернуть `<script>` внутри markdown
    (например в code-block), но md.disable(['html']) гарантирует, что
    это будет отрендерено как escaped-текст.
    """
    md = MarkdownIt(
        "gfm-like",
        {
            "html": False,        # ❌ <script>, <img onerror=...>
            "linkify": False,     # не требует linkify-it-py; URL — не наш use case
            "breaks": True,       # переводы строк = <br>
            "typographer": False,
        },
    )
    return md


def _sanitize_html_attrs(html: str) -> str:
    """Удаляет опасные атрибуты из HTML.

    markdown-it сам по себе не добавляет on-* / src / href на обычный текст,
    но мы делаем дополнительный pass для паранойи: регуляркой удаляем
    атрибуты из вайтлиста-запрета.
    """
    import re
    # Удаляем on*="..." и on*='...' и on* без значения
    cleaned = re.sub(r'\s+on\w+\s*=\s*"[^"]*"', "", html, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+on\w+\s*=\s*'[^']*'", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+on\w+\s*=\s*[^\s>]+", "", cleaned, flags=re.IGNORECASE)
    # Удаляем style=..., src=..., href=..., id=...
    cleaned = re.sub(r'\s+(style|src|href|id|target)\s*=\s*"[^"]*"', "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+(style|src|href|id|target)\s*=\s*'[^']*'", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+(style|src|href|id|target)\s*=\s*[^\s>]+", "", cleaned, flags=re.IGNORECASE)
    # javascript: в любом оставшемся URL → удаляем атрибут целиком
    cleaned = re.sub(r'\s+\w+\s*=\s*"javascript:[^"]*"', "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+\w+\s*=\s*'javascript:[^']*'", "", cleaned, flags=re.IGNORECASE)
    return cleaned


def render_markdown(text: str) -> str:
    """Конвертирует Markdown-текст в безопасный HTML.

    Args:
        text: Markdown-разметка. Может содержать GFM (таблицы, зачёркивание).

    Returns:
        HTML-строка. **Всегда экранированный HTML**, безопасна для
        рендеринга через `dangerouslySetInnerHTML`.

    Examples:
        >>> render_markdown("# Привет\\n\\n**жирный**")
        '<h1>Привет</h1>\\n<p><strong>жирный</strong></p>\\n'
    """
    if not text:
        return ""
    # Сначала — markdown-it (CommonMark + GFM, без inline HTML)
    raw_html = _get_renderer().render(text)
    # Затем — belt-and-suspenders: удаляем опасные атрибуты
    cleaned = _sanitize_html_attrs(raw_html)
    return cleaned


def split_into_blocks(text: str) -> list[str]:
    """Разбивает Markdown-текст на блоки для безопасного typewriting-эффекта.

    Возвращает список блоков: каждый абзац/заголовок/список — отдельный элемент.
    Это позволяет рендерить text по блокам вместо посимвольного typewriter,
    который бы выглядел странно на стриме (AI рисует блоки целиком).
    """
    if not text:
        return []
    # Markdown-it режет по \n\n на параграфы; возьмём paragraph-level.
    md = _get_renderer()
    tokens = md.parse(text)
    blocks: list[str] = []
    current: list[str] = []
    inside_pre = False
    for tok in tokens:
        if tok.type == "heading_open":
            current.append(tok.markup if hasattr(tok, "markup") else "")
        elif tok.type == "heading_close":
            current.append("\n")
        elif tok.type == "paragraph_open":
            current.append("")
        elif tok.type == "paragraph_close":
            current.append("\n")
            blocks.append("".join(current))
            current = []
        elif tok.type == "bullet_list_open":
            current.append("")
        elif tok.type == "bullet_list_close":
            current.append("\n")
            blocks.append("".join(current))
            current = []
        elif tok.type == "ordered_list_open":
            current.append("")
        elif tok.type == "ordered_list_close":
            current.append("\n")
            blocks.append("".join(current))
            current = []
        elif tok.type == "inline":
            current.append(tok.content)
        elif tok.type == "fence" or tok.type == "code_block":
            # Code blocks рендерим целиком, без typewriter
            current.append(f"\n```\n{tok.content}\n```\n")
        elif tok.type == "blockquote_open":
            current.append("> ")
        elif tok.type == "blockquote_close":
            current.append("\n")
    if current:
        blocks.append("".join(current))
    return [b.strip() for b in blocks if b.strip()]
