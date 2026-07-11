"""OpenAI LLM provider."""
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


class OpenAIProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model: str = "gpt-4.1") -> None:
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set")
        try:
            from openai import AsyncOpenAI, AuthenticationError, BadRequestError, RateLimitError
            from openai import APITimeoutError, APIConnectionError
        except ImportError as exc:
            raise ImportError("pip install openai") from exc

        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model
        self._AuthenticationError = AuthenticationError
        self._BadRequestError = BadRequestError
        self._RateLimitError = RateLimitError
        self._APITimeoutError = APITimeoutError
        self._APIConnectionError = APIConnectionError

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self._model

    async def complete(
        self,
        messages: list[dict[str, str]],
        config: LLMConfig,
    ) -> LLMResponse:
        model = config.model or self._model
        delay = _BASE_DELAY

        for attempt in range(_MAX_RETRIES):
            t0 = time.monotonic()
            try:
                resp = await self._client.chat.completions.create(
                    model=model,
                    messages=messages,  # type: ignore[arg-type]
                    temperature=config.temperature,
                    max_tokens=config.max_tokens,
                    timeout=config.timeout,
                )
                latency = (time.monotonic() - t0) * 1000
                usage = TokenUsage.from_counts(
                    model=model,
                    prompt=resp.usage.prompt_tokens if resp.usage else 0,
                    completion=resp.usage.completion_tokens if resp.usage else 0,
                )
                return LLMResponse(
                    content=resp.choices[0].message.content or "",
                    model=resp.model,
                    provider="openai",
                    usage=usage,
                    finish_reason=resp.choices[0].finish_reason or "stop",
                    latency_ms=latency,
                )
            except (self._AuthenticationError, self._BadRequestError) as exc:
                raise LLMAuthError(str(exc)) from exc
            except (self._RateLimitError, self._APITimeoutError, self._APIConnectionError) as exc:
                if attempt == _MAX_RETRIES - 1:
                    raise LLMRateLimitError(str(exc)) from exc
                _log.warning("openai_retry", attempt=attempt + 1, error=str(exc))
                await asyncio.sleep(min(delay, _MAX_DELAY))
                delay *= 2
            except Exception as exc:
                raise LLMProviderError(str(exc)) from exc

        raise LLMProviderError("OpenAI: max retries exceeded")

    async def stream(
        self,
        messages: list[dict[str, str]],
        config: LLMConfig,
    ) -> AsyncIterator[str]:
        model = config.model or self._model
        async with self._client.chat.completions.stream(
            model=model,
            messages=messages,  # type: ignore[arg-type]
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            timeout=config.timeout,
        ) as stream:
            async for chunk in stream:
                delta = chunk.choices[0].delta.content if chunk.choices else None
                if delta:
                    yield delta
