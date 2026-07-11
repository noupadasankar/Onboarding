"""Conversation service — creates, loads, and persists conversations."""
from __future__ import annotations

from app.chat.conversation_repository import ConversationRepository
from app.models.conversation import Conversation


class ConversationService:
    def __init__(self, repo: ConversationRepository) -> None:
        self._repo = repo

    def get_or_create(
        self,
        conversation_id: str | None,
        user_id: str,
        tenant: str = "default",
    ) -> Conversation:
        if conversation_id:
            conv = self._repo.get(conversation_id)
            if conv:
                return conv
        return self._repo.create(user_id=user_id, tenant=tenant)

    def save(self, conversation: Conversation) -> None:
        self._repo.save(conversation)

    def get(self, conversation_id: str) -> Conversation | None:
        return self._repo.get(conversation_id)

    def delete(self, conversation_id: str) -> bool:
        return self._repo.delete(conversation_id)
