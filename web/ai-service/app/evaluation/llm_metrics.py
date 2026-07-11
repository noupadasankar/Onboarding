"""LLM generation quality metrics.

Complements rag_metrics.py with measures that relate to the language
model's output rather than the retrieval pipeline.

Usage::

    from app.evaluation.llm_metrics import (
        response_latency_score,
        token_efficiency,
        hallucination_rate_estimate,
    )
"""
from __future__ import annotations

import re


def response_latency_score(latency_ms: float, target_ms: float = 3000.0) -> float:
    """Score latency on a 0–1 scale where 1 = at or below target.

    Falls off linearly to 0 at 2× the target.

    Args:
        latency_ms: Actual end-to-end latency.
        target_ms: Acceptable latency ceiling (default 3 s).
    """
    if latency_ms <= target_ms:
        return 1.0
    ratio = latency_ms / target_ms
    score = 1.0 - (ratio - 1.0)
    return max(0.0, round(score, 4))


def token_efficiency(answer: str, completion_tokens: int) -> float:
    """Estimate information density: characters per completion token.

    High values (> 4) indicate the model isn't padding with filler tokens.
    Normalised to [0, 1] with a ceiling of 6 chars/token = 1.0.

    Args:
        answer: The generated answer text.
        completion_tokens: Tokens consumed to produce the answer.
    """
    if not completion_tokens or not answer:
        return 0.0
    chars_per_token = len(answer) / completion_tokens
    return min(1.0, round(chars_per_token / 6.0, 4))


def hallucination_rate_estimate(
    answer: str,
    context: str,
    *,
    min_sentence_words: int = 5,
) -> float:
    """Rough hallucination rate: fraction of answer sentences with no overlap
    with the retrieved context.

    This is a heuristic proxy; the Governance Agent provides a higher-quality
    verdict using an LLM judge.

    Returns:
        Estimated hallucination rate in [0, 1] (lower is better).
    """
    if not answer.strip():
        return 0.0

    context_lower = context.lower()
    sentences = [s.strip() for s in re.split(r"[.!?]+", answer) if s.strip()]
    substantial = [s for s in sentences if len(s.split()) >= min_sentence_words]
    if not substantial:
        return 0.0

    hallucinated = 0
    for sent in substantial:
        words = [w.lower() for w in re.findall(r"\b[a-z]{3,}\b", sent)]
        if not words:
            continue
        overlap = sum(1 for w in words if w in context_lower)
        if overlap == 0:
            hallucinated += 1

    return round(hallucinated / len(substantial), 4)


def answer_completeness(answer: str, question: str) -> float:
    """Estimate how thoroughly the answer addresses the question.

    Checks whether key question terms appear in the answer.

    Returns:
        Completeness score in [0, 1].
    """
    if not question.strip() or not answer.strip():
        return 0.0

    # Extract content words from the question (exclude common stop words)
    _STOP = {"what", "how", "when", "where", "who", "which", "why", "the",
              "is", "are", "was", "were", "can", "could", "would", "should",
              "do", "does", "did", "a", "an", "in", "on", "at", "to", "of",
              "for", "with", "and", "or", "but", "i", "my", "me", "you"}
    q_words = {w.lower() for w in re.findall(r"\b[a-z]{2,}\b", question.lower())} - _STOP
    if not q_words:
        return 1.0

    a_words = {w.lower() for w in re.findall(r"\b[a-z]{2,}\b", answer.lower())}
    covered = q_words & a_words
    return round(len(covered) / len(q_words), 4)


def aggregate_llm_metrics(
    answer: str,
    question: str,
    context: str,
    completion_tokens: int,
    latency_ms: float,
    target_latency_ms: float = 3000.0,
) -> dict:
    """Return all LLM quality metrics as a single dict."""
    return {
        "response_latency_score": response_latency_score(latency_ms, target_latency_ms),
        "token_efficiency": token_efficiency(answer, completion_tokens),
        "hallucination_rate_estimate": hallucination_rate_estimate(answer, context),
        "answer_completeness": answer_completeness(answer, question),
    }
