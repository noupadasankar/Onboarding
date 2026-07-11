"""Anthropic LLM provider."""
from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator

from app.core.logging import get_logger
from app.llm.providers.base_provider import (
    BaseLLMProvider,
    LLMAuthError,
    LLMConfig,
    LLMProviderError,
    LLMRateLimitError,
    LLMResponse,
)
from app.llm.token_usage import TokenUsage

_log = get_logger()

_MAX_RETRIES = 3
_BASE_DELAY = 1.0
_MAX_DELAY = 30.0

# Anthropic models use a separate system message — extract it from the messages list.
_SYSTEM_ROLE = "system"


class AnthropicProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6") -> None:
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY is not set")
        try:
            import anthropic
        except ImportError as exc:
            raise ImportError("pip install anthropic") from exc

        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = model
        self._anthropic = anthropic

    @property
    def provider_name(self) -> str:
        return "anthropic"

    @property
    def model_name(self) -> str:
        return self._model

    @staticmethod
    def _split_messages(
        messages: list[dict[str, str]],
    ) -> tuple[str, list[dict[str, str]]]:
        """Extract system prompt; return (system_text, non_system_messages)."""
        system_parts: list[str] = []
        chat_messages: list[dict[str, str]] = []
        for m in messages:
            if m.get("role") == _SYSTEM_ROLE:
                system_parts.append(m["content"])
            else:
                chat_messages.append(m)
        return "\n\n".join(system_parts), chat_messages

    async def complete(
        self,
        messages: list[dict[str, str]],
        config: LLMConfig,
    ) -> LLMResponse:
        model = config.model or self._model
        system_text, chat_messages = self._split_messages(messages)
        delay = _BASE_DELAY

        for attempt in range(_MAX_RETRIES):
            t0 = time.monotonic()
            try:
                resp = await self._client.messages.create(
                    model=model,
                    system=system_text or anthropic.NOT_GIVEN,  # type: ignore[name-defined]
                    messages=chat_messages,  # type: ignore[arg-type]
                    temperature=config.temperature,
                    max_tokens=config.max_tokens,
                    timeout=config.timeout,
                )
                latency = (time.monotonic() - t0) * 1000
                content = resp.content[0].text if resp.content else ""
                usage = TokenUsage.from_counts(
                    model=model,
                    prompt=resp.usage.input_tokens,
                    completion=resp.usage.output_tokens,
                )
                return LLMResponse(
                    content=content,
                    model=resp.model,
                    provider="anthropic",
                    usage=usage,
                    finish_reason=resp.stop_reason or "stop",
                    latency_ms=latency,
                )
            except self._anthropic.AuthenticationError as exc:
                raise LLMAuthError(str(exc)) from exc
            except (
                self._anthropic.RateLimitError,
                self._anthropic.APITimeoutError,
                self._anthropic.APIConnectionError,
            ) as exc:
                if attempt == _MAX_RETRIES - 1:
                    raise LLMRateLimitError(str(exc)) from exc
                _log.warning("anthropic_retry", attempt=attempt + 1, error=str(exc))
                await asyncio.sleep(min(delay, _MAX_DELAY))
                delay *= 2
            except Exception as exc:
                raise LLMProviderError(str(exc)) from exc

        raise LLMProviderError("Anthropic: max retries exceeded")

    async def stream(
        self,
        messages: list[dict[str, str]],
        config: LLMConfig,
    ) -> AsyncIterator[str]:
        model = config.model or self._model
        system_text, chat_messages = self._split_messages(messages)

        async with self._client.messages.stream(
            model=model,
            system=system_text or self._anthropic.NOT_GIVEN,  # type: ignore[attr-defined]
            messages=chat_messages,  # type: ignore[arg-type]
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            timeout=config.timeout,
        ) as stream:
            async for text in stream.text_stream:
                yield text
