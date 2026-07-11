"""Conversation model — stores a multi-turn chat history."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from app.models.message import Message


class Conversation(BaseModel):
    conversation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    tenant: str = "default"
    messages: list[Message] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def add_message(self, role: str, content: str) -> None:
        from app.models.message import MessageRole
        self.messages.append(Message(role=MessageRole(role), content=content))
        self.updated_at = datetime.now(timezone.utc)

    def history_window(self, max_turns: int) -> list[Message]:
        """Return the last *max_turns* user+assistant pairs (non-system messages)."""
        chat = [m for m in self.messages if m.role != "system"]
        return chat[-(max_turns * 2):]

    def compress(self, summary_text: str) -> None:
        """Replace all messages with a single system summary message.

        Used by ConversationSummarizer when history grows too long.
        The summary preserves the semantic content of the conversation
        without sending every turn to the LLM.
        """
        from app.models.message import MessageRole
        summary_msg = Message(
            role=MessageRole.system,
            content=f"[Conversation summary]\n{summary_text}",
        )
        self.messages = [summary_msg]
        self.updated_at = datetime.now(timezone.utc)
