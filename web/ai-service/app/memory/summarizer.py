"""Conversation summarizer — compresses long histories into a summary message.

When a conversation exceeds ``max_turns`` turns, the oldest turns are
collapsed into a single system-level summary so the LLM context window
stays manageable without losing long-range context.

Usage::

    summarizer = ConversationSummarizer(llm_service)
    summary = await summarizer.summarize(conversation)
    conversation.compress(summary_text)
"""
from __future__ import annotations

from app.core.logging import get_logger
from app.llm.llm_service import LLMService
from app.models.conversation import Conversation

_log = get_logger()

_SUMMARIZE_SYSTEM = (
    "You are a helpful assistant that summarises conversation histories. "
    "Produce a concise factual summary in 3–5 sentences covering the main topics discussed, "
    "any decisions reached, and any information the user provided about themselves. "
    "Do NOT include opinions, greetings, or filler. Write in third person."
)


class ConversationSummarizer:
    """Summarises old conversation turns when history grows too long."""

    def __init__(self, llm_service: LLMService, threshold_turns: int = 20) -> None:
        self._llm = llm_service
        self.threshold_turns = threshold_turns

    async def maybe_summarize(self, conversation: Conversation) -> bool:
        """Summarise and compress history if it exceeds the threshold.

        Returns True if a summary was produced, False if not needed.
        """
        chat_messages = [m for m in conversation.messages if m.role.value != "system"]
        if len(chat_messages) < self.threshold_turns * 2:
            return False

        summary_text = await self.summarize(conversation)
        conversation.compress(summary_text)
        _log.info(
            "conversation_summarized",
            conversation_id=conversation.conversation_id,
            original_turns=len(chat_messages) // 2,
        )
        return True

    async def summarize(self, conversation: Conversation) -> str:
        """Produce a plain-text summary of the conversation so far."""
        history_text = "\n".join(
            f"{m.role.value.upper()}: {m.content}"
            for m in conversation.messages
            if m.role.value != "system"
        )
        messages = [
            {"role": "system", "content": _SUMMARIZE_SYSTEM},
            {"role": "user", "content": f"Summarise this conversation:\n\n{history_text}"},
        ]
        resp = await self._llm.complete(messages)
        return resp.content.strip()
