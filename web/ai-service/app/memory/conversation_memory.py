"""Conversation memory — loads history into graph state format.

Keeps the graph state free of Conversation model details.
"""
from __future__ import annotations

from app.chat.conversation_repository import ConversationRepository
from app.models.conversation import Conversation


def load_history(
    conversation_id: str | None,
    repo: ConversationRepository,
    max_turns: int = 10,
) -> tuple[Conversation | None, list[dict[str, str]]]:
    """Load a conversation and return (conversation, history_dicts).

    Args:
        conversation_id: Existing conversation ID to load (or None).
        repo: Conversation repository.
        max_turns: Max user+assistant turns to include.

    Returns:
        Tuple of (Conversation | None, list of role/content dicts).
    """
    if not conversation_id:
        return None, []
    conv = repo.get(conversation_id)
    if not conv:
        return None, []
    history = [
        {"role": m.role.value, "content": m.content}
        for m in conv.history_window(max_turns)
    ]
    return conv, history
