"""LLM service — thin wrapper that builds LLMConfig and delegates to a provider."""
from __future__ import annotations

from collections.abc import AsyncIterator

from app.core.config import get_settings
from app.core.logging import get_logger
from app.llm.llm_factory import create_llm_provider
from app.llm.providers.base_provider import BaseLLMProvider, LLMConfig, LLMResponse

_log = get_logger()


class LLMService:
    """Owns one provider instance; exposes complete() and stream()."""

    def __init__(self, provider: BaseLLMProvider | None = None) -> None:
        self._provider = provider or create_llm_provider()

    def _config(self, **overrides) -> LLMConfig:
        s = get_settings()
        return LLMConfig(
            model=overrides.get("model", s.llm_model),
            temperature=overrides.get("temperature", s.llm_temperature),
            max_tokens=overrides.get("max_tokens", s.llm_max_tokens),
            timeout=overrides.get("timeout", s.llm_timeout),
        )

    async def complete(
        self,
        messages: list[dict[str, str]],
        **overrides,
    ) -> LLMResponse:
        config = self._config(**overrides)
        _log.info(
            "llm_complete",
            provider=self._provider.provider_name,
            model=config.model,
            n_messages=len(messages),
        )
        return await self._provider.complete(messages, config)

    async def stream(
        self,
        messages: list[dict[str, str]],
        **overrides,
    ) -> AsyncIterator[str]:
        config = self._config(**overrides)
        _log.info(
            "llm_stream",
            provider=self._provider.provider_name,
            model=config.model,
        )
        return self._provider.stream(messages, config)

    @property
    def provider_name(self) -> str:
        return self._provider.provider_name

    @property
    def model_name(self) -> str:
        return self._provider.model_name
