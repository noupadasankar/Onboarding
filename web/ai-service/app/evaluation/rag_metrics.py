"""RAG evaluation metrics.

Computes retrieval and generation quality scores without requiring
an external evaluation framework.  All metrics return float in [0, 1]
(higher is better) unless documented otherwise.

Usage::

    from app.evaluation.rag_metrics import (
        retrieval_precision,
        context_relevance,
        answer_groundedness,
        citation_coverage,
    )

    precision = retrieval_precision(retrieved_chunks, relevant_ids)
    relevance = context_relevance(question, context_text)
"""
from __future__ import annotations

import re
from collections import Counter


# ---------------------------------------------------------------------------
# Retrieval metrics
# ---------------------------------------------------------------------------

def retrieval_precision(retrieved_ids: list[str], relevant_ids: set[str]) -> float:
    """Fraction of retrieved chunks that are actually relevant.

    Args:
        retrieved_ids: Chunk IDs returned by the retrieval pipeline.
        relevant_ids: Ground-truth set of relevant chunk IDs.

    Returns:
        Precision in [0, 1].
    """
    if not retrieved_ids:
        return 0.0
    hits = sum(1 for cid in retrieved_ids if cid in relevant_ids)
    return hits / len(retrieved_ids)


def retrieval_recall(retrieved_ids: list[str], relevant_ids: set[str]) -> float:
    """Fraction of relevant chunks that were actually retrieved.

    Args:
        retrieved_ids: Chunk IDs returned by the retrieval pipeline.
        relevant_ids: Ground-truth set of relevant chunk IDs.

    Returns:
        Recall in [0, 1].  Returns 1.0 if relevant_ids is empty.
    """
    if not relevant_ids:
        return 1.0
    hits = sum(1 for cid in relevant_ids if cid in retrieved_ids)
    return hits / len(relevant_ids)


def retrieval_f1(retrieved_ids: list[str], relevant_ids: set[str]) -> float:
    """Harmonic mean of precision and recall."""
    p = retrieval_precision(retrieved_ids, relevant_ids)
    r = retrieval_recall(retrieved_ids, relevant_ids)
    if p + r == 0:
        return 0.0
    return 2 * p * r / (p + r)


# ---------------------------------------------------------------------------
# Context relevance (lexical overlap proxy)
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> Counter:
    tokens = re.findall(r"\b[a-z]{3,}\b", text.lower())
    return Counter(tokens)


def context_relevance(question: str, context: str) -> float:
    """Estimate how relevant the retrieved context is to the question.

    Uses lexical overlap (Jaccard on content words) as a proxy.
    A production system should use a cross-encoder reranker instead.

    Returns:
        Relevance score in [0, 1].
    """
    if not context.strip():
        return 0.0
    q_tokens = set(_tokenize(question))
    c_tokens = set(_tokenize(context))
    if not q_tokens:
        return 0.0
    intersection = q_tokens & c_tokens
    union = q_tokens | c_tokens
    return len(intersection) / len(union)


# ---------------------------------------------------------------------------
# Answer groundedness
# ---------------------------------------------------------------------------

def answer_groundedness(answer: str, context: str) -> float:
    """Estimate what fraction of answer sentences are grounded in context.

    A sentence is considered grounded if it shares ≥ 2 content words
    with the context.  This is a rough proxy; production systems use
    an NLI model or the Governance Agent's LLM verdict.

    Returns:
        Groundedness in [0, 1].
    """
    if not answer.strip():
        return 0.0
    context_tokens = set(_tokenize(context))
    sentences = [s.strip() for s in re.split(r"[.!?]+", answer) if s.strip()]
    if not sentences:
        return 0.0
    grounded = 0
    for sent in sentences:
        s_tokens = set(_tokenize(sent))
        overlap = s_tokens & context_tokens
        if len(overlap) >= 2:
            grounded += 1
    return grounded / len(sentences)


# ---------------------------------------------------------------------------
# Citation accuracy
# ---------------------------------------------------------------------------

def citation_coverage(answer: str, citations: list[dict]) -> float:
    """Fraction of cited sources whose content appears in the answer.

    Checks whether the filename or a key phrase from each citation is
    mentioned in the answer.

    Returns:
        Coverage in [0, 1].  Returns 1.0 if no citations provided.
    """
    if not citations:
        return 1.0
    answer_lower = answer.lower()
    covered = 0
    for cit in citations:
        filename = (cit.get("filename") or "").lower()
        text = (cit.get("text") or "").lower()
        # A citation is "covered" if the filename stem appears in the answer
        # or at least 3 content words from the chunk appear in the answer.
        stem = filename.rsplit(".", 1)[0].replace("_", " ").replace("-", " ")
        if stem and stem in answer_lower:
            covered += 1
            continue
        chunk_words = set(_tokenize(text))
        ans_words = set(_tokenize(answer))
        if len(chunk_words & ans_words) >= 3:
            covered += 1
    return covered / len(citations)


# ---------------------------------------------------------------------------
# Aggregated report
# ---------------------------------------------------------------------------

def evaluate_response(
    question: str,
    context: str,
    answer: str,
    citations: list[dict],
    retrieved_ids: list[str] | None = None,
    relevant_ids: set[str] | None = None,
) -> dict:
    """Compute all available RAG metrics and return as a dict."""
    result: dict = {
        "context_relevance": round(context_relevance(question, context), 4),
        "answer_groundedness": round(answer_groundedness(answer, context), 4),
        "citation_coverage": round(citation_coverage(answer, citations), 4),
    }
    if retrieved_ids is not None and relevant_ids is not None:
        result["retrieval_precision"] = round(retrieval_precision(retrieved_ids, relevant_ids), 4)
        result["retrieval_recall"] = round(retrieval_recall(retrieved_ids, relevant_ids), 4)
        result["retrieval_f1"] = round(retrieval_f1(retrieved_ids, relevant_ids), 4)
    return result
