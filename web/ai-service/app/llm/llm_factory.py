"""LLM provider factory — maps provider name → concrete implementation."""
from __future__ import annotations

from app.core.config import get_settings
from app.llm.providers.base_provider import BaseLLMProvider


def create_llm_provider(provider_name: str | None = None) -> BaseLLMProvider:
    """Return a configured LLM provider.

    Args:
        provider_name: Override the ``LLM_PROVIDER`` setting. One of:
            ``"openai"``, ``"anthropic"``, ``"local"``.

    Raises:
        ValueError: Unknown provider name.
        ValueError: Required API key not configured.
    """
    s = get_settings()
    name = (provider_name or s.llm_provider).lower().strip()

    if name == "openai":
        from app.llm.providers.openai_provider import OpenAIProvider
        return OpenAIProvider(api_key=s.openai_api_key, model=s.llm_model, base_url=s.openai_base_url)

    if name == "anthropic":
        from app.llm.providers.anthropic_provider import AnthropicProvider
        return AnthropicProvider(api_key=s.anthropic_api_key, model=s.llm_model)

    if name == "local":
        from app.llm.providers.local_provider import LocalLLMProvider
        return LocalLLMProvider()

    raise ValueError(
        f"Unknown LLM provider: {name!r}. "
        "Supported: openai, anthropic, local."
    )
