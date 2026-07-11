"""Tests for token_counter module."""
import pytest

from app.embeddings.token_counter import (
    count_tokens,
    estimate_cost,
    max_input_tokens,
    texts_exceed_limit,
)


class TestCountTokens:
    def test_empty_string(self) -> None:
        assert count_tokens("") >= 0

    def test_single_word_at_least_one_token(self) -> None:
        assert count_tokens("hello") >= 1

    def test_more_text_more_tokens(self) -> None:
        short = count_tokens("hi")
        long = count_tokens("hello world " * 100)
        assert long > short

    def test_returns_int(self) -> None:
        assert isinstance(count_tokens("test"), int)

    def test_model_arg_accepted(self) -> None:
        # Should not raise for any supported model name
        result = count_tokens("test", model="text-embedding-3-small")
        assert result >= 1


class TestEstimateCost:
    def test_zero_tokens_zero_cost(self) -> None:
        assert estimate_cost(0) == 0.0

    def test_known_model_positive_cost(self) -> None:
        cost = estimate_cost(1_000, model="text-embedding-3-small")
        assert cost > 0.0

    def test_local_model_zero_cost(self) -> None:
        assert estimate_cost(1_000_000, model="local-hash-v1") == 0.0

    def test_unknown_model_zero_cost(self) -> None:
        assert estimate_cost(1_000, model="nonexistent-model") == 0.0

    def test_proportional_to_tokens(self) -> None:
        c1 = estimate_cost(1_000, model="text-embedding-3-small")
        c2 = estimate_cost(2_000, model="text-embedding-3-small")
        assert abs(c2 - 2 * c1) < 1e-12


class TestMaxInputTokens:
    def test_openai_small_limit(self) -> None:
        assert max_input_tokens("text-embedding-3-small") == 8_191

    def test_voyage_higher_limit(self) -> None:
        assert max_input_tokens("voyage-3-large") > 8_191

    def test_unknown_model_returns_default(self) -> None:
        assert max_input_tokens("unknown-model") == 8_191


class TestTextsExceedLimit:
    def test_short_texts_pass(self) -> None:
        texts = ["short text"] * 5
        assert texts_exceed_limit(texts, "text-embedding-3-small") == []

    def test_returns_indexes_of_long_texts(self) -> None:
        # A very long string should exceed the limit for any model
        long = "hello world " * 10_000
        short = "hi"
        indexes = texts_exceed_limit([short, long], "text-embedding-3-small")
        assert 1 in indexes
        assert 0 not in indexes
