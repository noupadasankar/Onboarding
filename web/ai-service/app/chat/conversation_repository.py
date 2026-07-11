"""In-memory conversation repository.

Implements the same interface a PostgreSQL or Redis-backed repository would
expose, so swapping the storage backend requires no changes to callers.
"""
from __future__ import annotations

import threading

from app.models.conversation import Conversation


class ConversationRepository:
    """Thread-safe in-memory store keyed by conversation_id."""

    def __init__(self) -> None:
        self._store: dict[str, Conversation] = {}
        self._lock = threading.Lock()

    def create(self, user_id: str, tenant: str = "default") -> Conversation:
        conv = Conversation(user_id=user_id, tenant=tenant)
        with self._lock:
            self._store[conv.conversation_id] = conv
        return conv

    def get(self, conversation_id: str) -> Conversation | None:
        with self._lock:
            return self._store.get(conversation_id)

    def save(self, conversation: Conversation) -> None:
        with self._lock:
            self._store[conversation.conversation_id] = conversation

    def delete(self, conversation_id: str) -> bool:
        with self._lock:
            return self._store.pop(conversation_id, None) is not None

    def list_for_user(self, user_id: str) -> list[Conversation]:
        with self._lock:
            return [c for c in self._store.values() if c.user_id == user_id]

    def count(self) -> int:
        with self._lock:
            return len(self._store)


# ── Process-wide singleton ────────────────────────────────────────────────────

_repo: ConversationRepository | None = None
_repo_lock = threading.Lock()


def get_conversation_repository() -> ConversationRepository:
    global _repo
    with _repo_lock:
        if _repo is None:
            _repo = ConversationRepository()
    return _repo


def reset_conversation_repository() -> None:
    """For test isolation."""
    global _repo
    with _repo_lock:
        _repo = None
