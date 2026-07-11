"""Shared fixtures for vectorstore tests.

Uses ChromaDB EphemeralClient (in-memory) so tests run without a server.
"""
from __future__ import annotations

import pytest

from app.embeddings.providers.local_provider import LocalProvider
from app.models.chunk import Chunk
from app.models.document import FileType
from app.models.embedded_chunk import EmbeddedChunk
from app.repositories.vector_repository import VectorRepository
from app.services.vector_service import VectorService
from app.vectorstore.chroma_client import ChromaClient


# ── In-memory Chroma fixtures ─────────────────────────────────────────────────

@pytest.fixture
def memory_client() -> ChromaClient:
    """Fresh in-memory ChromaDB client (no server required)."""
    return ChromaClient(mode="memory")


@pytest.fixture
def repo(memory_client: ChromaClient) -> VectorRepository:
    """VectorRepository backed by in-memory ChromaDB."""
    return VectorRepository(client=memory_client, collection_name="test_collection")


@pytest.fixture
def vector_service(repo: VectorRepository) -> VectorService:
    """VectorService backed by in-memory repository."""
    return VectorService(repo)


# ── Data factories ────────────────────────────────────────────────────────────

DOC_ID = "aaaabbbb-cccc-dddd-eeee-ffffffffffff"
DOC_ID_2 = "bbbbcccc-dddd-eeee-ffff-aaaaaaaaaaaa"


def make_chunk(idx: int = 0, doc_id: str = DOC_ID) -> Chunk:
    return Chunk(
        chunk_id=Chunk.build_id(doc_id, idx),
        document_id=doc_id,
        chunk_index=idx,
        text=f"This is chunk {idx} of the employee handbook section on leave policy. " * 5,
        token_count=50 + idx,
        section="Leave Policy",
        metadata={
            "filename": "handbook.txt",
            "file_type": FileType.TXT,
            "department": "HR",
            "category": "policy",
            "source": "test/handbook.txt",
        },
    )


def make_embedded(
    chunk: Chunk,
    dims: int = 16,
) -> tuple[EmbeddedChunk, str]:
    provider = LocalProvider(dimensions=dims)
    import asyncio
    vecs = asyncio.get_event_loop().run_until_complete(
        provider.embed_batch([chunk.text])
    )
    ec = EmbeddedChunk(
        chunk_id=chunk.chunk_id,
        document_id=chunk.document_id,
        embedding=vecs[0],
        dimensions=dims,
        provider="local",
        model="local-hash-v1",
        token_count=chunk.token_count,
        metadata=dict(chunk.metadata),
    )
    return ec, chunk.text


def make_embedded_batch(
    n: int = 3,
    doc_id: str = DOC_ID,
    dims: int = 16,
) -> tuple[list[EmbeddedChunk], dict[str, str]]:
    """Return (list[EmbeddedChunk], chunk_texts dict)."""
    chunks = [make_chunk(i, doc_id) for i in range(n)]
    ecs = []
    texts: dict[str, str] = {}
    for c in chunks:
        ec, text = make_embedded(c, dims)
        ecs.append(ec)
        texts[ec.chunk_id] = text
    return ecs, texts
