"""Tests for TokenUsage."""
from app.llm.token_usage import TokenUsage


class TestTokenUsage:
    def test_total_is_sum(self) -> None:
        u = TokenUsage.from_counts("gpt-4.1", prompt=100, completion=50)
        assert u.total_tokens == 150

    def test_prompt_and_completion_stored(self) -> None:
        u = TokenUsage.from_counts("gpt-4.1", prompt=200, completion=80)
        assert u.prompt_tokens == 200
        assert u.completion_tokens == 80

    def test_known_model_has_positive_cost(self) -> None:
        u = TokenUsage.from_counts("gpt-4.1", prompt=1_000_000, completion=1_000_000)
        assert u.estimated_cost_usd > 0

    def test_unknown_model_cost_is_zero(self) -> None:
        u = TokenUsage.from_counts("unknown-model-xyz", prompt=1000, completion=500)
        assert u.estimated_cost_usd == 0.0

    def test_to_dict_has_all_keys(self) -> None:
        u = TokenUsage.from_counts("gpt-4.1", prompt=10, completion=5)
        d = u.to_dict()
        assert set(d) == {"prompt_tokens", "completion_tokens", "total_tokens", "estimated_cost_usd"}

    def test_zero_tokens(self) -> None:
        u = TokenUsage.from_counts("gpt-4.1", prompt=0, completion=0)
        assert u.total_tokens == 0
        assert u.estimated_cost_usd == 0.0
