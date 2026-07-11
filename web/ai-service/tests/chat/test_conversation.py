"""Tests for conversation models and repository."""
import pytest

from app.chat.conversation_repository import ConversationRepository
from app.chat.conversation_service import ConversationService
from app.models.conversation import Conversation
from app.models.message import MessageRole


class TestConversationModel:
    def test_new_conversation_has_no_messages(self) -> None:
        c = Conversation(user_id="u1")
        assert c.messages == []

    def test_add_message_appends(self) -> None:
        c = Conversation(user_id="u1")
        c.add_message("user", "Hello")
        assert len(c.messages) == 1
        assert c.messages[0].role == MessageRole.USER

    def test_add_assistant_message(self) -> None:
        c = Conversation(user_id="u1")
        c.add_message("assistant", "Hi there!")
        assert c.messages[0].role == MessageRole.ASSISTANT

    def test_history_window_respects_max_turns(self) -> None:
        c = Conversation(user_id="u1")
        for i in range(6):
            c.add_message("user", f"q{i}")
            c.add_message("assistant", f"a{i}")
        # max_turns=2 → last 4 messages
        window = c.history_window(max_turns=2)
        assert len(window) == 4

    def test_history_window_excludes_system(self) -> None:
        c = Conversation(user_id="u1")
        c.add_message("system", "You are OptiAgent.")
        c.add_message("user", "Q")
        c.add_message("assistant", "A")
        window = c.history_window(max_turns=10)
        assert all(m.role != MessageRole.SYSTEM for m in window)

    def test_conversation_id_is_uuid(self) -> None:
        c = Conversation(user_id="u1")
        assert len(c.conversation_id) == 36  # UUID string length


class TestConversationRepository:
    def test_create_and_get(self) -> None:
        repo = ConversationRepository()
        conv = repo.create(user_id="u1", tenant="acme")
        fetched = repo.get(conv.conversation_id)
        assert fetched is not None
        assert fetched.conversation_id == conv.conversation_id

    def test_get_nonexistent_returns_none(self) -> None:
        repo = ConversationRepository()
        assert repo.get("nonexistent-id") is None

    def test_save_updates_existing(self) -> None:
        repo = ConversationRepository()
        conv = repo.create(user_id="u1")
        conv.add_message("user", "Hello")
        repo.save(conv)
        fetched = repo.get(conv.conversation_id)
        assert fetched is not None
        assert len(fetched.messages) == 1

    def test_delete_returns_true_when_found(self) -> None:
        repo = ConversationRepository()
        conv = repo.create(user_id="u1")
        assert repo.delete(conv.conversation_id) is True

    def test_delete_returns_false_when_not_found(self) -> None:
        repo = ConversationRepository()
        assert repo.delete("does-not-exist") is False

    def test_count_tracks_conversations(self) -> None:
        repo = ConversationRepository()
        repo.create(user_id="u1")
        repo.create(user_id="u2")
        assert repo.count() == 2

    def test_list_for_user_filters(self) -> None:
        repo = ConversationRepository()
        repo.create(user_id="alice")
        repo.create(user_id="alice")
        repo.create(user_id="bob")
        results = repo.list_for_user("alice")
        assert len(results) == 2
        assert all(c.user_id == "alice" for c in results)


class TestConversationService:
    def test_creates_new_when_no_id(self) -> None:
        repo = ConversationRepository()
        svc = ConversationService(repo)
        conv = svc.get_or_create(None, "u1")
        assert conv.user_id == "u1"
        assert conv.conversation_id in [c.conversation_id for c in repo.list_for_user("u1")]

    def test_resumes_existing_by_id(self) -> None:
        repo = ConversationRepository()
        svc = ConversationService(repo)
        existing = repo.create(user_id="u1")
        resumed = svc.get_or_create(existing.conversation_id, "u1")
        assert resumed.conversation_id == existing.conversation_id

    def test_creates_new_when_id_not_found(self) -> None:
        repo = ConversationRepository()
        svc = ConversationService(repo)
        conv = svc.get_or_create("nonexistent-id", "u1")
        assert conv.conversation_id != "nonexistent-id"
