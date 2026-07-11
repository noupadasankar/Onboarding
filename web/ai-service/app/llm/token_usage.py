"""Token usage tracking and cost estimation."""
from __future__ import annotations

from dataclasses import dataclass, field


# Cost per 1M tokens (USD) — approximate, update as pricing changes
_COST_PER_1M_INPUT: dict[str, float] = {
    "gpt-4.1": 2.00,
    "gpt-4o": 2.50,
    "gpt-4o-mini": 0.15,
    "gpt-4-turbo": 10.00,
    "claude-sonnet-4-6": 3.00,
    "claude-haiku-4-5-20251001": 0.80,
    "claude-opus-4-8": 15.00,
}
_COST_PER_1M_OUTPUT: dict[str, float] = {
    "gpt-4.1": 8.00,
    "gpt-4o": 10.00,
    "gpt-4o-mini": 0.60,
    "gpt-4-turbo": 30.00,
    "claude-sonnet-4-6": 15.00,
    "claude-haiku-4-5-20251001": 4.00,
    "claude-opus-4-8": 75.00,
}


@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0

    @classmethod
    def from_counts(cls, model: str, prompt: int, completion: int) -> "TokenUsage":
        total = prompt + completion
        input_cost = _COST_PER_1M_INPUT.get(model, 0.0) * prompt / 1_000_000
        output_cost = _COST_PER_1M_OUTPUT.get(model, 0.0) * completion / 1_000_000
        return cls(
            prompt_tokens=prompt,
            completion_tokens=completion,
            total_tokens=total,
            estimated_cost_usd=round(input_cost + output_cost, 8),
        )

    def to_dict(self) -> dict:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": self.estimated_cost_usd,
        }
