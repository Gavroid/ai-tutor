"""HermesProvider — реальный провайдер (OpenAI-compatible, включая MiniMax Anthropic endpoint).

Особенности MiniMax:
- base_url: https://api.minimax.io/anthropic
- формат сообщений — Anthropic Messages API (system отдельно, messages — list)
- НО мы используем OpenAI-compatible обёртку, если она доступна, иначе прямое Anthropic API.

Для простоты используем OpenAI-compatible chat completions, что подходит для
большинства провайдеров (включая OpenRouter, MiniMax v1, OpenAI).
"""
from __future__ import annotations

import html
import json
import logging
import re
from typing import Any

import httpx
from app.ai.sanitize import sanitize_output, sanitize_user_input
from app.ai.types import AIMessage, AIProvider, AIRequest, AIResponse
from app.config import get_settings

logger = logging.getLogger(__name__)



_THINK_BLOCK_RE = re.compile(r"(?is)<think\b[^>]*>.*?</think>")
_ESCAPED_THINK_BLOCK_RE = re.compile(r"(?is)&lt;think\b[^&]*&gt;.*?&lt;/think&gt;")
_FENCED_JSON_RE = re.compile(r"(?is)```(?:json)?\s*(\{.*?\})\s*```")
_FENCE_LINE_RE = re.compile(r"(?m)^\s*```[a-zA-Z0-9_-]*\s*$")
_MARKDOWN_TABLE_SEPARATOR_RE = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$")


def _strip_reasoning_blocks(text: str) -> str:
    """Remove provider reasoning/code-fence artefacts before parsing or displaying output."""
    if not text:
        return ""
    text = _THINK_BLOCK_RE.sub("", text)
    text = _ESCAPED_THINK_BLOCK_RE.sub("", text)
    text = _FENCE_LINE_RE.sub("", text)
    cleaned_lines: list[str] = []
    for line in text.splitlines():
        if _MARKDOWN_TABLE_SEPARATOR_RE.match(line):
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines).strip()


def _find_first_json_object(text: str) -> str | None:
    """Return the first balanced JSON object substring, ignoring prose around it."""
    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escaped = False
    for idx in range(start, len(text)):
        ch = text[idx]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : idx + 1]
    return None


def _extract_structured_json(text: str) -> dict | None:
    """Extract structured JSON from raw/fenced/prose-prefixed model output."""
    if not text:
        return None
    candidates: list[str] = []
    unescaped = html.unescape(text.strip())
    for source in (text.strip(), unescaped):
        fenced = _FENCED_JSON_RE.search(source)
        if fenced:
            candidates.append(fenced.group(1))
        obj = _find_first_json_object(source)
        if obj:
            candidates.append(obj)
        candidates.append(source)

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def _prepare_model_output(raw_content: str) -> tuple[str, dict | None]:
    """Clean raw provider output and parse structure before HTML escaping."""
    cleaned_raw = _strip_reasoning_blocks(raw_content)
    structured = _extract_structured_json(cleaned_raw)
    if structured is not None:
        display_content = json.dumps(structured, ensure_ascii=False)
        return display_content, structured
    return sanitize_output(cleaned_raw), structured


class HermesProviderError(Exception):
    """Ошибка вызова AI API (после retry). Безопасна для логирования (без ключа)."""


class HermesProvider(AIProvider):
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout: int = 30,
        max_retries: int = 2,
        max_input_chars: int = 8000,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        self.max_input_chars = max_input_chars

    async def ping(self) -> bool:
        """Проверка соединения. НЕ выводит ключ."""
        url = f"{self.base_url}/models"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(url, headers=headers)
                return r.status_code < 500
        except Exception as exc:  # noqa: BLE001
            logger.warning("AI ping failed: %r", exc)
            return False

    async def complete(self, req: AIRequest) -> AIResponse:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Системное сообщение выделяем отдельно, остальное — массив
        system_parts: list[str] = []
        messages_payload: list[dict[str, Any]] = []
        for m in req.messages:
            content = sanitize_user_input(m.content, self.max_input_chars)
            if m.role == "system":
                system_parts.append(content)
            else:
                messages_payload.append({"role": m.role, "content": content})

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages_payload,
            "max_tokens": req.max_tokens,
            "temperature": req.temperature,
        }
        if system_parts:
            # OpenAI-стиль: одно system-сообщение в начале.
            # Если провайдер не поддерживает, можно вынести в messages[0].
            payload["messages"] = [{"role": "system", "content": "\n\n".join(system_parts)}] + messages_payload

        # Retry с экспоненциальной задержкой
        last_exc: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    r = await client.post(url, json=payload, headers=headers)
                if r.status_code >= 500:
                    raise HermesProviderError(f"HTTP {r.status_code}")
                if r.status_code >= 400:
                    # 4xx — не повторяем, это клиентская ошибка
                    body = r.text[:500]
                    logger.error("AI 4xx: %s | body[:500]=%s", r.status_code, body)
                    raise HermesProviderError(f"HTTP {r.status_code}: {body}")
                data = r.json()
                break
            except (httpx.HTTPError, HermesProviderError) as exc:
                last_exc = exc
                if attempt >= self.max_retries:
                    raise HermesProviderError(f"AI request failed after {attempt + 1} attempts") from exc
                import asyncio

                await asyncio.sleep(2 ** attempt)
        else:  # pragma: no cover
            raise HermesProviderError("unreachable")

        # Парсим ответ (OpenAI-compatible формат)
        try:
            choice = data["choices"][0]
            raw_content = choice["message"]["content"] or ""
            usage = data.get("usage", {})
            input_tokens = int(usage.get("prompt_tokens", 0))
            output_tokens = int(usage.get("completion_tokens", 0))
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise HermesProviderError(f"Bad response shape: {exc}") from exc

        # Clean visible output and parse structured JSON before HTML escaping.
        content, structured = _prepare_model_output(raw_content)

        return AIResponse(
            content=content,
            model=data.get("model", self.model),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            structured=structured,
        )


def build_provider() -> AIProvider:
    """Фабрика: deterministic > HermesProvider > MockProvider.

    Порядок приоритета (Sprint 2):
    1) ai_deterministic_mode=True → MockProvider безусловно;
    2) иначе ключ задан/валидный → HermesProvider;
    3) иначе MockProvider (no network).
    """
    settings = get_settings()
    if getattr(settings, "ai_deterministic_mode", False):
        logger.info("AI deterministic mode → MockProvider (Sprint 2)")
        from app.ai.mock import MockProvider

        return MockProvider()
    key = settings.ai_api_key or ""
    # Заглушки/тестовые ключи → mock
    if (
        not key
        or key.startswith("change_me")
        or key == "mock-key-for-tests"
        or "mock" in key.lower()
    ):
        logger.info("AI_API_KEY не задан или placeholder — используется MockProvider")
        from app.ai.mock import MockProvider

        return MockProvider()
    return HermesProvider(
        base_url=settings.ai_base_url,
        api_key=settings.ai_api_key,
        model=settings.ai_model,
        timeout=settings.ai_timeout_seconds,
        max_retries=settings.ai_max_retries,
        max_input_chars=settings.ai_max_input_chars,
    )
