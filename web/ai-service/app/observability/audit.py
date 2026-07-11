"""Audit logging — structured records of every AI interaction.

Every call that flows through GraphRunner produces one AuditRecord.
Records are written to the structured logger and can be forwarded to
any sink (database, S3, SIEM) by attaching a log handler.

Usage::

    audit = AuditLogger()
    record = audit.record(...)
    audit.write(record)
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from app.core.logging import get_logger

_log = get_logger()


@dataclass
class AuditRecord:
    """Immutable audit log entry for one AI interaction."""

    audit_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)

    # Request
    user_id: str = ""
    tenant: str = "default"
    conversation_id: str = ""
    question: str = ""
    department: str | None = None

    # Routing
    selected_agent: str = ""
    routing_method: str = ""  # "keyword" | "llm" | "fallback"

    # Retrieval
    chunks_retrieved: int = 0
    retrieved_document_ids: list[str] = field(default_factory=list)

    # Generation
    llm_model: str = ""
    llm_provider: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    estimated_cost_usd: float = 0.0

    # Governance
    governance_grounded: bool | None = None
    governance_confidence: float | None = None
    governance_revised: bool = False

    # Response
    answer_length: int = 0
    citations_count: int = 0
    latency_ms: float = 0.0

    # Errors
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class AuditLogger:
    """Writes AuditRecords to the structured log stream."""

    def record_from_state(self, state: dict, user_id: str, latency_ms: float) -> AuditRecord:
        """Build an AuditRecord from a completed GraphState dict."""
        meta = state.get("metadata", {}) or {}
        errors = state.get("errors", []) or []
        citations = state.get("citations", []) or []
        answer = state.get("answer", "") or ""

        from app.llm.token_usage import TokenUsage
        usage = TokenUsage.from_counts(
            model=state.get("model", ""),
            prompt=state.get("prompt_tokens", 0),
            completion=state.get("completion_tokens", 0),
        )

        # Collect retrieved document IDs from citations
        doc_ids = list({c.get("filename", "") for c in citations if c.get("filename")})
        chunks_found = (
            meta.get("hr_chunks_found")
            or meta.get("finance_chunks_found")
            or meta.get("it_chunks_found")
            or 0
        )

        return AuditRecord(
            user_id=user_id,
            tenant=state.get("tenant", "default"),
            conversation_id=state.get("conversation_id", ""),
            question=state.get("question", ""),
            department=state.get("department"),
            selected_agent=state.get("selected_agent", ""),
            routing_method=meta.get("routing_method", ""),
            chunks_retrieved=chunks_found,
            retrieved_document_ids=doc_ids,
            llm_model=state.get("model", ""),
            llm_provider=state.get("provider", ""),
            prompt_tokens=state.get("prompt_tokens", 0),
            completion_tokens=state.get("completion_tokens", 0),
            estimated_cost_usd=usage.estimated_cost_usd,
            governance_grounded=meta.get("governance_grounded"),
            governance_confidence=meta.get("governance_confidence"),
            governance_revised="governance_answer_revised" in str(meta),
            answer_length=len(answer),
            citations_count=len(citations),
            latency_ms=latency_ms,
            errors=errors,
            metadata=meta,
        )

    def write(self, record: AuditRecord) -> None:
        """Emit the audit record as a structured log event."""
        _log.info(
            "audit_record",
            audit_id=record.audit_id,
            user_id=record.user_id,
            tenant=record.tenant,
            conversation_id=record.conversation_id,
            selected_agent=record.selected_agent,
            routing_method=record.routing_method,
            llm_model=record.llm_model,
            prompt_tokens=record.prompt_tokens,
            completion_tokens=record.completion_tokens,
            estimated_cost_usd=record.estimated_cost_usd,
            governance_grounded=record.governance_grounded,
            governance_confidence=record.governance_confidence,
            governance_revised=record.governance_revised,
            answer_length=record.answer_length,
            citations_count=record.citations_count,
            latency_ms=record.latency_ms,
            chunks_retrieved=record.chunks_retrieved,
            errors_count=len(record.errors),
        )
