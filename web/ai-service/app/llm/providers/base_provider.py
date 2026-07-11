"""Abstract base for all LLM providers."""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass

from app.llm.token_usage import TokenUsage


@dataclass
class LLMConfig:
    model: str = ""
    temperature: float = 0.0
    max_tokens: int = 1024
    timeout: int = 60


@dataclass
class LLMResponse:
    content: str
    model: str
    provider: str
    usage: TokenUsage
    finish_reason: str = "stop"
    latency_ms: float = 0.0


class LLMProviderError(RuntimeError):
    """Raised when a provider call fails after retries."""


class LLMAuthError(LLMProviderError):
    """Raised on authentication / API key errors — do not retry."""


class LLMRateLimitError(LLMProviderError):
    """Raised on rate-limit errors — caller may retry with backoff."""


class BaseLLMProvider(ABC):
    """Contract all LLM providers must satisfy."""

    @abstractmethod
    async def complete(
        self,
        messages: list[dict[str, str]],
        config: LLMConfig,
    ) -> LLMResponse: ...

    @abstractmethod
    async def stream(
        self,
        messages: list[dict[str, str]],
        config: LLMConfig,
    ) -> AsyncIterator[str]: ...

    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @property
    @abstractmethod
    def model_name(self) -> str: ...
