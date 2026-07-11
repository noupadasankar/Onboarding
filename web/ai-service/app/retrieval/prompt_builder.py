"""Prompt builder — assembles the final LLM prompt from context + question.

The prompt structure follows best practices for grounded, citation-backed RAG:
  1. System persona / role.
  2. Hard constraint: answer only from provided context.
  3. Fallback instruction: what to say when the answer is not in context.
  4. The assembled context (from ContextBuilder).
  5. The user question.

The builder is intentionally not tied to any LLM SDK — it produces plain strings
that any provider (OpenAI, Anthropic, Gemini) can consume.

Usage::

    builder = PromptBuilder()
    prompt = builder.build(context="...", query="How many leave days?")
"""
from __future__ import annotations

from dataclasses import dataclass, field


# ── Default template ──────────────────────────────────────────────────────────

_DEFAULT_SYSTEM = """\
You are OptiAgent, an AI HR assistant for Deloitte employees.
Your role is to answer HR-related questions accurately and professionally.

Rules:
- Answer ONLY using the information provided in the Context section below.
- If the answer is not found in the context, respond with exactly:
  "I couldn't find that information in the uploaded HR documents."
- Do not invent, assume, or extrapolate HR policies.
- When quoting policy, reference the source document and section if available.
- Keep answers concise and well-structured.\
"""

_DEFAULT_CONTEXT_HEADER = "### Context (retrieved from HR documents)\n\n"
_DEFAULT_QUESTION_HEADER = "\n\n### Question\n\n"
_DEFAULT_INSTRUCTION_FOOTER = "\n\n### Answer\n\n"


@dataclass
class PromptTemplate:
    """Configurable prompt template.

    Swap this out to change the persona (e.g. Finance Assistant, IT Helpdesk).
    """

    system_prompt: str = _DEFAULT_SYSTEM
    context_header: str = _DEFAULT_CONTEXT_HEADER
    question_header: str = _DEFAULT_QUESTION_HEADER
    instruction_footer: str = _DEFAULT_INSTRUCTION_FOOTER
    no_context_reply: str = (
        "I couldn't find that information in the uploaded HR documents."
    )


class PromptBuilder:
    """Builds a grounded RAG prompt string.

    Args:
        template: PromptTemplate instance. Defaults to the OptiAgent HR template.
    """

    def __init__(self, template: PromptTemplate | None = None) -> None:
        self.template = template or PromptTemplate()

    def build(self, context: str, query: str) -> str:
        """Return the full prompt string.

        Args:
            context: Assembled context from ContextBuilder (may be empty).
            query: Normalised user question.

        Returns:
            Full prompt text (system + context + question).
        """
        t = self.template

        if not context.strip():
            # No context retrieved — use fallback instruction
            return (
                f"{t.system_prompt}\n\n"
                f"{t.context_header}"
                f"(No relevant documents were found.)\n\n"
                f"{t.question_header.lstrip()}{query}"
                f"{t.instruction_footer}"
                f"{t.no_context_reply}"
            )

        return (
            f"{t.system_prompt}\n\n"
            f"{t.context_header}"
            f"{context}"
            f"{t.question_header.lstrip()}{query}"
            f"{t.instruction_footer}"
        )

    def build_messages(
        self,
        context: str,
        query: str,
    ) -> list[dict[str, str]]:
        """Return OpenAI / Anthropic messages-array format.

        Returns:
            [{"role": "system", "content": ...}, {"role": "user", "content": ...}]
        """
        t = self.template
        ctx_block = context.strip() or "(No relevant documents were found.)"

        user_content = (
            f"{t.context_header}{ctx_block}"
            f"{t.question_header.lstrip()}{query}"
        )

        return [
            {"role": "system", "content": t.system_prompt},
            {"role": "user", "content": user_content},
        ]
