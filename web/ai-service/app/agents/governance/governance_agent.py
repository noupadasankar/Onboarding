"""Governance Agent — validates AI answers for groundedness before returning them.

Parses the LLM's JSON output and, if the answer is not grounded, replaces it
with the revised answer the Governance Agent provides.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from app.core.logging import get_logger
from app.llm.llm_service import LLMService
from app.models.graph_state import GraphState

_log = get_logger()
_SYSTEM = (Path(__file__).parent.parent.parent / "prompts" / "governance_system.md").read_text(encoding="utf-8")

_PASS_THROUGH_CONFIDENCE = 0.5  # Below this → use revised_answer


def _build_messages(question: str, context: str, answer: str) -> list[dict]:
    user_content = (
        f"Question: {question}\n\n"
        f"Context:\n{context or '(none)'}\n\n"
        f"Answer to validate:\n{answer}"
    )
    return [
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": user_content},
    ]


async def governance_node(state: GraphState, llm_service: LLMService) -> dict:
    """Validate the answer produced by a domain agent.

    If the answer is not grounded (confidence < threshold or grounded=false),
    replaces it with the Governance Agent's revised answer.
    """
    answer = state.get("answer", "")
    context = state.get("retrieved_context", "")
    question = state.get("question", "")

    # Skip validation if there is no answer to validate
    if not answer:
        return {}

    t0 = time.monotonic()
    try:
        resp = await llm_service.complete(_build_messages(question, context, answer))
        raw = resp.content.strip()

        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = "\n".join(raw.split("\n")[1:])
            raw = raw.rstrip("`").strip()

        verdict = json.loads(raw)
        grounded = bool(verdict.get("grounded", True))
        confidence = float(verdict.get("confidence", 1.0))
        issues = verdict.get("issues", [])
        revised = verdict.get("revised_answer")

        latency = round((time.monotonic() - t0) * 1000, 1)
        _log.info(
            "governance_validation",
            grounded=grounded,
            confidence=confidence,
            issues_count=len(issues),
            latency_ms=latency,
        )

        updates: dict = {
            "metadata": {
                **state.get("metadata", {}),
                "governance_grounded": grounded,
                "governance_confidence": confidence,
                "governance_issues": issues,
                "governance_latency_ms": latency,
            }
        }

        if not grounded or confidence < _PASS_THROUGH_CONFIDENCE:
            if revised:
                updates["answer"] = revised
                _log.warning("governance_answer_revised", confidence=confidence)

        return updates

    except (json.JSONDecodeError, ValueError) as exc:
        # Governance parse failure — pass original answer through unchanged
        _log.warning("governance_parse_failed", error=str(exc))
        return {
            "metadata": {
                **state.get("metadata", {}),
                "governance_error": str(exc),
            }
        }
    except Exception as exc:
        _log.warning("governance_llm_failed", error=str(exc))
        return {
            "errors": [*state.get("errors", []), f"Governance error: {exc}"],
        }
