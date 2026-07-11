"""Token counter for the embedding pipeline.

Distinct from the chunking token counter in ``app/chunking/token_counter.py``.
This module focuses on:
  * Counting tokens per embedding model (different encodings per provider).
  * Estimating API cost before embedding (helps with budgeting).
  * Checking batch token limits.

Model token limits (soft caps — API may accept slightly more):
  text-embedding-3-small : 8 191 tokens per text
  text-embedding-3-large : 8 191 tokens per text
  text-embedding-ada-002  : 8 191 tokens per text
  voyage-3-large          : 32 000 tokens per text
"""
from __future__ import annotations

# Try tiktoken for accurate counts (already a project dependency from Increment 4)
try:
    import tiktoken as _tiktoken
    _HAS_TIKTOKEN = True
except ImportError:
    _HAS_TIKTOKEN = False

# ── Per-model encoding names (tiktoken) ───────────────────────────────────────

_OPENAI_ENCODING = "cl100k_base"   # used by all OpenAI embedding models

# ── Per-model cost in USD per 1 000 tokens (approximate, as of 2025) ─────────

_COST_PER_1K: dict[str, float] = {
    "text-embedding-3-small": 0.00002,
    "text-embedding-3-large": 0.00013,
    "text-embedding-ada-002": 0.00010,
    "voyage-3-large": 0.00006,
    "voyage-3": 0.00003,
    "local-hash-v1": 0.0,        # free
}

# ── Per-model max input tokens ────────────────────────────────────────────────

_MAX_INPUT_TOKENS: dict[str, int] = {
    "text-embedding-3-small": 8_191,
    "text-embedding-3-large": 8_191,
    "text-embedding-ada-002": 8_191,
    "voyage-3-large": 32_000,
    "voyage-3": 32_000,
    "local-hash-v1": 99_999,
}

_DEFAULT_MAX_TOKENS = 8_191


# ── Public API ────────────────────────────────────────────────────────────────

def count_tokens(text: str, model: str = "text-embedding-3-small") -> int:
    """Count the tokens in *text* for *model*.

    Uses tiktoken when available; falls back to ``max(1, len(text) // 4)``.
    """
    if _HAS_TIKTOKEN:
        # All current OpenAI embedding models use cl100k_base
        enc = _tiktoken.get_encoding(_OPENAI_ENCODING)
        return len(enc.encode(text))
    return max(1, len(text) // 4)


def estimate_cost(total_tokens: int, model: str = "text-embedding-3-small") -> float:
    """Estimate USD cost for embedding *total_tokens* with *model*.

    Returns 0.0 for unknown models rather than raising.
    """
    rate = _COST_PER_1K.get(model, 0.0)
    return (total_tokens / 1_000) * rate


def max_input_tokens(model: str) -> int:
    """Return the maximum tokens per text for *model*."""
    return _MAX_INPUT_TOKENS.get(model, _DEFAULT_MAX_TOKENS)


def texts_exceed_limit(texts: list[str], model: str) -> list[int]:
    """Return indices of texts whose token count exceeds the model's limit."""
    limit = max_input_tokens(model)
    return [i for i, t in enumerate(texts) if count_tokens(t, model) > limit]
