"""Tests for LLM factory."""
import pytest

from app.llm.providers.local_provider import LocalLLMProvider


class TestLLMFactory:
    def test_local_provider_created(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("app.llm.llm_factory.get_settings", lambda: _Cfg("local"))
        from app.llm.llm_factory import create_llm_provider
        p = create_llm_provider()
        assert isinstance(p, LocalLLMProvider)

    def test_explicit_local_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("app.llm.llm_factory.get_settings", lambda: _Cfg("openai"))
        from app.llm.llm_factory import create_llm_provider
        p = create_llm_provider(provider_name="local")
        assert isinstance(p, LocalLLMProvider)

    def test_unknown_provider_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("app.llm.llm_factory.get_settings", lambda: _Cfg("unknown"))
        from app.llm.llm_factory import create_llm_provider
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            create_llm_provider()

    def test_openai_missing_key_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("app.llm.llm_factory.get_settings", lambda: _Cfg("openai", openai_key=""))
        from app.llm.llm_factory import create_llm_provider
        with pytest.raises(ValueError):
            create_llm_provider()

    def test_anthropic_missing_key_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("app.llm.llm_factory.get_settings", lambda: _Cfg("anthropic", anthropic_key=""))
        from app.llm.llm_factory import create_llm_provider
        with pytest.raises(ValueError):
            create_llm_provider()


class _Cfg:
    def __init__(
        self,
        provider: str,
        openai_key: str = "sk-fake",
        anthropic_key: str = "ant-fake",
        model: str = "gpt-4.1",
    ) -> None:
        self.llm_provider = provider
        self.openai_api_key = openai_key
        self.anthropic_api_key = anthropic_key
        self.llm_model = model
