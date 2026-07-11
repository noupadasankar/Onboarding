"""Local/mock LLM provider — deterministic responses, no API key, for tests."""
from __future__ import annotations

from collections.abc import AsyncIterator

from app.llm.providers.base_provider import BaseLLMProvider, LLMConfig, LLMResponse
from app.llm.token_usage import TokenUsage

_MOCK_ANSWER = (
    "Based on the provided HR documents, employees are entitled to 20 days of "
    "annual leave per year. Requests must be submitted at least two weeks in advance."
)


class LocalLLMProvider(BaseLLMProvider):
    """Returns a deterministic mock answer — used in tests and local dev."""

    def __init__(self, response: str = _MOCK_ANSWER) -> None:
        self._response = response

    @property
    def provider_name(self) -> str:
        return "local"

    @property
    def model_name(self) -> str:
        return "local-mock-v1"

    async def complete(
        self,
        messages: list[dict[str, str]],
        config: LLMConfig,
    ) -> LLMResponse:
        prompt_tokens = sum(len(m.get("content", "").split()) * 2 for m in messages)
        completion_tokens = len(self._response.split()) * 2
        return LLMResponse(
            content=self._response,
            model="local-mock-v1",
            provider="local",
            usage=TokenUsage.from_counts("local-mock-v1", prompt_tokens, completion_tokens),
            finish_reason="stop",
            latency_ms=1.0,
        )

    async def stream(
        self,
        messages: list[dict[str, str]],
        config: LLMConfig,
    ) -> AsyncIterator[str]:
        for word in self._response.split(" "):
            yield word + " "
