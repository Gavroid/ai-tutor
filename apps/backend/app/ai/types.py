"""Контракт AI-провайдера и DTO.

Реализации:
- `HermesProvider` — реальный провайдер (OpenAI-compatible, MiniMax через Anthropic endpoint)
- `MockProvider` — детерминированные ответы для тестов и разработки без ключа
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol

Mode = Literal["explain", "hint", "check", "generate", "diagnose", "chat", "quiz"]
Role = Literal["system", "user", "assistant"]


@dataclass(slots=True)
class AIMessage:
    role: Role
    content: str


@dataclass(slots=True)
class AIRequest:
    messages: list[AIMessage]
    mode: Mode = "chat"
    max_tokens: int = 1024
    temperature: float = 0.4
    # Доп. контекст для логирования/трассировки (НЕ уходит в LLM)
    context_meta: dict = field(default_factory=dict)


@dataclass(slots=True)
class AIResponse:
    content: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    confidence: float = 1.0
    # Структурированный JSON, если LLM вернул его (например, для check/generate).
    # Парсится из content, если content начинается с { и валиден как JSON.
    structured: dict | None = None
    raw_error: str | None = None
    # Sprint 4.1.3: источники RAG (для UI индикатор "📖 Источник").
    # Список dict: {chunk_id, material_id, material_title, page_number}.
    sources: list[dict] = field(default_factory=list)


class AIProvider(Protocol):
    async def complete(self, req: AIRequest) -> AIResponse: ...
    async def ping(self) -> bool: ...