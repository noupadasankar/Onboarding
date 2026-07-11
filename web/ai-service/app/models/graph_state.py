"""Shared LangGraph workflow state.

Passed through every node as a single object. Node functions return a dict
with only the fields they modify; LangGraph merges the updates into state.

Keep this as a TypedDict (not Pydantic) — LangGraph requires TypedDict.
"""
from __future__ import annotations

from typing import Any, TypedDict


class GraphState(TypedDict, total=False):
    # ── Input ─────────────────────────────────────────────────────────────────
    question: str
    user_id: str
    conversation_id: str
    tenant: str
    department: str | None
    document_id: str | None
    top_k: int
    min_score: float

    # ── Routing ───────────────────────────────────────────────────────────────
    # Supervisor writes this; downstream nodes read it.
    selected_agent: str  # "hr" | "unknown"

    # ── Retrieval ─────────────────────────────────────────────────────────────
    retrieved_context: str
    citations: list[dict[str, Any]]

    # ── Generation ────────────────────────────────────────────────────────────
    answer: str
    model: str
    provider: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: float

    # ── Conversation history ──────────────────────────────────────────────────
    # List of {"role": "user"|"assistant", "content": str} dicts
    messages: list[dict[str, str]]

    # ── Metadata & errors ─────────────────────────────────────────────────────
    errors: list[str]
    metadata: dict[str, Any]
