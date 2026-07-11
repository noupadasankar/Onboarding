"""Tests for LLM providers."""
import asyncio

import pytest

from app.llm.providers.base_provider import (
    BaseLLMProvider,
    LLMConfig,
    LLMProviderError,
)
from app.llm.providers.local_provider import LocalLLMProvider


class TestLocalProvider:
    def test_provider_name(self) -> None:
        assert LocalLLMProvider().provider_name == "local"

    def test_model_name(self) -> None:
        assert LocalLLMProvider().model_name == "local-mock-v1"

    def test_complete_returns_response(self) -> None:
        provider = LocalLLMProvider()
        cfg = LLMConfig()
        result = asyncio.get_event_loop().run_until_complete(
            provider.complete([{"role": "user", "content": "hi"}], cfg)
        )
        assert len(result.content) > 0

    def test_complete_provider_field(self) -> None:
        result = asyncio.get_event_loop().run_until_complete(
            LocalLLMProvider().complete([{"role": "user", "content": "hi"}], LLMConfig())
        )
        assert result.provider == "local"

    def test_complete_usage_populated(self) -> None:
        result = asyncio.get_event_loop().run_until_complete(
            LocalLLMProvider().complete([{"role": "user", "content": "hi"}], LLMConfig())
        )
        assert result.usage.total_tokens > 0

    def test_custom_response(self) -> None:
        p = LocalLLMProvider(response="Custom answer.")
        result = asyncio.get_event_loop().run_until_complete(
            p.complete([{"role": "user", "content": "q"}], LLMConfig())
        )
        assert result.content == "Custom answer."

    def test_stream_yields_tokens(self) -> None:
        p = LocalLLMProvider(response="Hello world test.")

        async def _collect() -> list[str]:
            tokens = []
            async for t in await p.stream([{"role": "user", "content": "q"}], LLMConfig()):
                tokens.append(t)
            return tokens

        tokens = asyncio.get_event_loop().run_until_complete(_collect())
        assert len(tokens) > 0
        assert "Hello" in "".join(tokens)

    def test_finish_reason_stop(self) -> None:
        result = asyncio.get_event_loop().run_until_complete(
            LocalLLMProvider().complete([{"role": "user", "content": "q"}], LLMConfig())
        )
        assert result.finish_reason == "stop"


class TestBaseLLMProviderABC:
    def test_cannot_instantiate_abstract(self) -> None:
        with pytest.raises(TypeError):
            BaseLLMProvider()  # type: ignore[abstract]


class TestOpenAIProviderInitGuard:
    def test_missing_api_key_raises(self) -> None:
        from app.llm.providers.openai_provider import OpenAIProvider
        with pytest.raises(ValueError, match="OPENAI_API_KEY"):
            OpenAIProvider(api_key="")


class TestAnthropicProviderInitGuard:
    def test_missing_api_key_raises(self) -> None:
        from app.llm.providers.anthropic_provider import AnthropicProvider
        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
            AnthropicProvider(api_key="")

    def test_split_messages_extracts_system(self) -> None:
        from app.llm.providers.anthropic_provider import AnthropicProvider
        messages = [
            {"role": "system", "content": "You are OptiAgent."},
            {"role": "user", "content": "Hi"},
        ]
        system, chat = AnthropicProvider._split_messages(messages)
        assert "OptiAgent" in system
        assert len(chat) == 1
        assert chat[0]["role"] == "user"

    def test_split_messages_no_system(self) -> None:
        from app.llm.providers.anthropic_provider import AnthropicProvider
        messages = [{"role": "user", "content": "Hi"}]
        system, chat = AnthropicProvider._split_messages(messages)
        assert system == ""
        assert len(chat) == 1
