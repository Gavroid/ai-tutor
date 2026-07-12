"""HermesProvider — реальный провайдер (OpenAI-compatible, включая MiniMax Anthropic endpoint).

Особенности MiniMax:
- base_url: https://api.minimax.io/anthropic
- формат сообщений — Anthropic Messages API (system отдельно, messages — list)
- НО мы используем OpenAI-compatible обёртку, если она доступна, иначе прямое Anthropic API.

Для простоты используем OpenAI-compatible chat completions, что подходит для
большинства провайдеров (включая OpenRouter, MiniMax v1, OpenAI).
"""
from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from app.ai.sanitize import sanitize_output, sanitize_user_input
from app.ai.types import AIMessage, AIRequest, AIResponse, AIProvider
from app.config import get_settings

logger = logging.getLogger(__name__)


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

        # Sanitize output
        content = sanitize_output(raw_content)

        # Пытаемся распарсить структурированный JSON, если он есть
        structured: dict | None = None
        stripped = content.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            try:
                structured = json.loads(stripped)
            except json.JSONDecodeError:
                pass

        return AIResponse(
            content=content,
            model=data.get("model", self.model),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            structured=structured,
        )


def build_provider() -> AIProvider:
    """Фабрика: вернёт HermesProvider, если есть ключ, иначе MockProvider."""
    settings = get_settings()
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