"""Tests for EmbeddingFactory."""
import pytest

from app.embeddings.embedding_factory import EmbeddingFactory
from app.embeddings.providers.local_provider import LocalProvider


class TestEmbeddingFactory:
    def test_create_local_provider(self) -> None:
        p = EmbeddingFactory.create("local")
        assert isinstance(p, LocalProvider)

    def test_unknown_provider_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown embedding provider"):
            EmbeddingFactory.create("nonexistent-provider")

    def test_available_providers_contains_known(self) -> None:
        available = EmbeddingFactory.available_providers()
        assert "local" in available
        assert "openai" in available
        assert "voyage" in available

    def test_create_is_case_insensitive(self) -> None:
        p = EmbeddingFactory.create("LOCAL")
        assert isinstance(p, LocalProvider)

    def test_create_strips_whitespace(self) -> None:
        p = EmbeddingFactory.create("  local  ")
        assert isinstance(p, LocalProvider)

    def test_create_openai_without_key_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """OpenAI provider must raise ValueError when the API key is missing."""

        def _bad_init(self, **kw: object) -> None:
            raise ValueError("OPENAI_API_KEY is not set")

        monkeypatch.setattr(
            "app.embeddings.providers.openai_provider.OpenAIProvider.__init__",
            _bad_init,
        )
        with pytest.raises(ValueError, match="OPENAI_API_KEY"):
            EmbeddingFactory.create("openai")
