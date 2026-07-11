"""Tests for app/observability/audit.py."""
import time

import pytest

from app.observability.audit import AuditLogger, AuditRecord


def _sample_state(**overrides) -> dict:
    state = {
        "question": "How many leave days?",
        "answer": "You receive 20 days of annual leave.",
        "conversation_id": "conv-1",
        "tenant": "acme",
        "selected_agent": "hr",
        "model": "gpt-4.1",
        "provider": "openai",
        "prompt_tokens": 150,
        "completion_tokens": 50,
        "citations": [{"filename": "handbook.pdf", "page": 3}],
        "retrieved_context": "20 days of annual leave.",
        "errors": [],
        "metadata": {
            "routing_method": "keyword",
            "hr_chunks_found": 2,
            "governance_grounded": True,
            "governance_confidence": 0.95,
        },
    }
    state.update(overrides)
    return state


class TestAuditRecord:
    def test_audit_id_is_set(self) -> None:
        record = AuditRecord()
        assert record.audit_id
        assert len(record.audit_id) > 8

    def test_timestamp_is_recent(self) -> None:
        before = time.time()
        record = AuditRecord()
        after = time.time()
        assert before <= record.timestamp <= after

    def test_default_tenant(self) -> None:
        record = AuditRecord()
        assert record.tenant == "default"


class TestAuditLoggerRecordFromState:
    def _logger(self) -> AuditLogger:
        return AuditLogger()

    def test_user_id_copied(self) -> None:
        record = self._logger().record_from_state(_sample_state(), user_id="u-42", latency_ms=200.0)
        assert record.user_id == "u-42"

    def test_selected_agent_copied(self) -> None:
        record = self._logger().record_from_state(_sample_state(), user_id="u-1", latency_ms=100.0)
        assert record.selected_agent == "hr"

    def test_routing_method_from_metadata(self) -> None:
        record = self._logger().record_from_state(_sample_state(), user_id="u-1", latency_ms=100.0)
        assert record.routing_method == "keyword"

    def test_chunks_retrieved_from_metadata(self) -> None:
        record = self._logger().record_from_state(_sample_state(), user_id="u-1", latency_ms=100.0)
        assert record.chunks_retrieved == 2

    def test_citations_count(self) -> None:
        record = self._logger().record_from_state(_sample_state(), user_id="u-1", latency_ms=100.0)
        assert record.citations_count == 1

    def test_answer_length(self) -> None:
        state = _sample_state()
        record = self._logger().record_from_state(state, user_id="u-1", latency_ms=100.0)
        assert record.answer_length == len(state["answer"])

    def test_latency_recorded(self) -> None:
        record = self._logger().record_from_state(_sample_state(), user_id="u-1", latency_ms=312.5)
        assert record.latency_ms == 312.5

    def test_governance_fields_copied(self) -> None:
        record = self._logger().record_from_state(_sample_state(), user_id="u-1", latency_ms=100.0)
        assert record.governance_grounded is True
        assert record.governance_confidence == pytest.approx(0.95)

    def test_doc_ids_extracted_from_citations(self) -> None:
        record = self._logger().record_from_state(_sample_state(), user_id="u-1", latency_ms=100.0)
        assert "handbook.pdf" in record.retrieved_document_ids

    def test_errors_empty_by_default(self) -> None:
        record = self._logger().record_from_state(_sample_state(), user_id="u-1", latency_ms=100.0)
        assert record.errors == []

    def test_errors_propagated(self) -> None:
        state = _sample_state(errors=["something went wrong"])
        record = self._logger().record_from_state(state, user_id="u-1", latency_ms=100.0)
        assert "something went wrong" in record.errors


class TestAuditLoggerWrite:
    def test_write_does_not_raise(self) -> None:
        logger = AuditLogger()
        record = logger.record_from_state(_sample_state(), user_id="u-1", latency_ms=100.0)
        logger.write(record)  # should not raise
