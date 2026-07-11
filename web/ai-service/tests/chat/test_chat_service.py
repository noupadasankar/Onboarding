"""Integration tests for ChatService using LocalProvider + in-memory Chroma."""
import asyncio
import uuid

import pytest

from app.chat.chat_service import ChatService
from app.chat.conversation_repository import ConversationRepository
from app.embeddings.embedding_pipeline import EmbeddingPipeline
from app.embeddings.providers.local_provider import LocalProvider
from app.llm.llm_service import LLMService
from app.llm.providers.local_provider import LocalLLMProvider
from app.models.chunk import Chunk
from app.repositories.vector_repository import VectorRepository
from app.schemas.chat import ChatRequest
from app.services.vector_service import VectorService
from app.vectorstore.chroma_client import ChromaClient


_DIMS = 64


def _make_vec_svc() -> VectorService:
    client = ChromaClient(mode="memory")
    repo = VectorRepository(client=client, collection_name=f"chat_{uuid.uuid4().hex[:8]}")
    return VectorService(repo)


def _make_chunk(text: str, idx: int = 0) -> Chunk:
    return Chunk(
        chunk_id=f"c{idx}",
        document_id="doc1",
        chunk_index=idx,
        text=text,
        token_count=len(text.split()),
    )


def _index_chunks(svc: VectorService, texts: list[str]) -> None:
    provider = LocalProvider(dimensions=_DIMS)
    chunks = [_make_chunk(t, i) for i, t in enumerate(texts)]
    pipeline = EmbeddingPipeline(provider=provider)
    embedded = asyncio.get_event_loop().run_until_complete(pipeline.run(chunks))
    chunk_texts = {c.chunk_id: c.text for c in chunks}
    svc.index(embedded, chunk_texts)


@pytest.fixture
def chat_service() -> ChatService:
    vec_svc = _make_vec_svc()
    _index_chunks(vec_svc, [
        "Employees receive 20 days of annual leave per year.",
        "Sick leave entitlement is 5 days without a doctor note.",
        "Public holidays: the company observes 10 public holidays.",
    ])
    llm = LLMService(provider=LocalLLMProvider())
    repo = ConversationRepository()
    return ChatService(vector_service=vec_svc, llm_service=llm, conv_repo=repo)


class TestChatServiceBasic:
    def test_returns_chat_response(self, chat_service: ChatService) -> None:
        req = ChatRequest(question="How many leave days?")
        result = asyncio.get_event_loop().run_until_complete(
            chat_service.chat(req, user_id="u1")
        )
        assert result.answer

    def test_response_has_conversation_id(self, chat_service: ChatService) -> None:
        req = ChatRequest(question="How many leave days?")
        result = asyncio.get_event_loop().run_until_complete(
            chat_service.chat(req, user_id="u1")
        )
        assert len(result.conversation_id) == 36  # UUID

    def test_citations_is_list(self, chat_service: ChatService) -> None:
        req = ChatRequest(question="leave policy")
        result = asyncio.get_event_loop().run_until_complete(
            chat_service.chat(req, user_id="u1")
        )
        assert isinstance(result.citations, list)

    def test_usage_populated(self, chat_service: ChatService) -> None:
        req = ChatRequest(question="How many sick days?")
        result = asyncio.get_event_loop().run_until_complete(
            chat_service.chat(req, user_id="u1")
        )
        assert result.usage.total_tokens > 0

    def test_provider_field_set(self, chat_service: ChatService) -> None:
        req = ChatRequest(question="leave days")
        result = asyncio.get_event_loop().run_until_complete(
            chat_service.chat(req, user_id="u1")
        )
        assert result.provider == "local"

    def test_model_field_set(self, chat_service: ChatService) -> None:
        req = ChatRequest(question="leave days")
        result = asyncio.get_event_loop().run_until_complete(
            chat_service.chat(req, user_id="u1")
        )
        assert result.model


class TestChatServiceConversationHistory:
    def test_conversation_continues_with_same_id(self, chat_service: ChatService) -> None:
        req1 = ChatRequest(question="How many leave days?")
        r1 = asyncio.get_event_loop().run_until_complete(
            chat_service.chat(req1, user_id="u1")
        )
        req2 = ChatRequest(
            question="Can unused leave be carried over?",
            conversation_id=r1.conversation_id,
        )
        r2 = asyncio.get_event_loop().run_until_complete(
            chat_service.chat(req2, user_id="u1")
        )
        assert r2.conversation_id == r1.conversation_id

    def test_new_conversation_on_unknown_id(self, chat_service: ChatService) -> None:
        req = ChatRequest(
            question="How many leave days?",
            conversation_id="00000000-0000-0000-0000-000000000000",
        )
        result = asyncio.get_event_loop().run_until_complete(
            chat_service.chat(req, user_id="u1")
        )
        # New conversation created — different ID
        assert result.conversation_id != "00000000-0000-0000-0000-000000000000"
