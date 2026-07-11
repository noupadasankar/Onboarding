"""Vector service — business logic on top of VectorRepository.

Responsibilities:
  * Accept EmbeddedChunk lists from the embedding pipeline.
  * Build (EmbeddedChunk, text) pairs for the repository.
  * Manage the upsert pipeline (batch, duplicate detection).
  * Expose delete, stats, health helpers.

This is the only layer the API and higher-level pipelines should call.
"""
from __future__ import annotations

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.embedded_chunk import EmbeddedChunk
from app.models.vector_document import CollectionStats, VectorDocument, VectorSearchResult
from app.repositories.vector_repository import VectorRepository
from app.vectorstore.chroma_client import ChromaClient, get_chroma_client
from app.vectorstore.search_filters import SearchFilters

_log = get_logger()


class VectorService:
    """Orchestrates vector storage operations.

    Args:
        repository: VectorRepository to delegate persistence to.
    """

    def __init__(self, repository: VectorRepository) -> None:
        self._repo = repository

    # ── Indexing ──────────────────────────────────────────────────────────────

    def index(
        self,
        embedded_chunks: list[EmbeddedChunk],
        chunk_texts: dict[str, str],
    ) -> int:
        """Upsert *embedded_chunks* into the vector store.

        Args:
            embedded_chunks: List produced by the embedding pipeline.
            chunk_texts: Mapping of chunk_id → original text (for ChromaDB document field).

        Returns:
            Number of vectors upserted.
        """
        if not embedded_chunks:
            return 0

        items: list[tuple[EmbeddedChunk, str]] = []
        for ec in embedded_chunks:
            text = chunk_texts.get(ec.chunk_id, "")
            items.append((ec, text))

        count = self._repo.upsert_batch(items)
        _log.info(
            "vector_service_indexed",
            count=count,
            document_id=embedded_chunks[0].document_id if embedded_chunks else "",
        )
        return count

    def reindex_document(
        self,
        document_id: str,
        embedded_chunks: list[EmbeddedChunk],
        chunk_texts: dict[str, str],
    ) -> int:
        """Delete existing vectors for *document_id*, then insert fresh ones.

        Used when a document is re-uploaded or re-processed.
        """
        deleted = self._repo.delete_document(document_id)
        _log.info("vector_service_reindex_delete", document_id=document_id, deleted=deleted)
        return self.index(embedded_chunks, chunk_texts)

    # ── Deletion ──────────────────────────────────────────────────────────────

    def delete_document(self, document_id: str) -> int:
        """Remove all vectors for *document_id*.  Returns chunk count deleted."""
        return self._repo.delete_document(document_id)

    def delete_chunk(self, chunk_id: str) -> bool:
        """Remove a single vector.  Returns True if it existed."""
        return self._repo.delete_chunk(chunk_id)

    # ── Retrieval ─────────────────────────────────────────────────────────────

    def get_document_vectors(self, document_id: str) -> list[VectorDocument]:
        """Return all stored VectorDocuments for *document_id*."""
        return self._repo.get_by_document(document_id)

    def get_chunk_vector(self, chunk_id: str) -> VectorDocument | None:
        """Return the stored VectorDocument for *chunk_id*, or None."""
        return self._repo.get_chunk(chunk_id)

    def is_indexed(self, document_id: str) -> bool:
        """Return True if any vectors for *document_id* are stored."""
        return bool(self._repo.get_by_document(document_id))

    # ── Search (used by Increment 7) ──────────────────────────────────────────

    def search(
        self,
        query_embedding: list[float],
        n_results: int = 5,
        department: str | None = None,
        document_id: str | None = None,
    ) -> list[VectorSearchResult]:
        """Semantic nearest-neighbour search.

        Args:
            query_embedding: Embedded query vector.
            n_results: Maximum results.
            department: Optional metadata filter.
            document_id: Optional restrict to a single document.

        Returns:
            Ordered list of VectorSearchResult (highest similarity first).
        """
        sf = SearchFilters()
        if department:
            sf.by_department(department)
        if document_id:
            sf.by_document(document_id)
        where = sf.build()
        return self._repo.search(query_embedding, n_results=n_results, where=where)

    # ── Stats / health ────────────────────────────────────────────────────────

    def health(self) -> bool:
        """Return True if the underlying collection is reachable."""
        return self._repo.health()

    def stats(self) -> CollectionStats:
        """Return collection statistics."""
        s = get_settings()
        return self._repo.stats(
            embedding_model=s.embedding_model,
            embedding_dimensions=s.embedding_dimensions,
        )

    def total_chunks(self) -> int:
        """Total number of vectors in the collection."""
        return self._repo.count()

    def unique_document_count(self) -> int:
        """Number of distinct documents in the collection."""
        return len(self._repo.unique_document_ids())

    def get_all_text(
        self,
        department: "str | None" = None,
    ) -> "list[dict]":
        """Return all chunk texts and metadata for BM25 index construction.

        Args:
            department: Optional department filter to scope the corpus.

        Returns:
            List of dicts with keys: chunk_id, text, document_id, metadata.
        """
        sf = SearchFilters()
        if department:
            sf.by_department(department)
        where = sf.build()
        return self._repo.get_all_text(where=where)


# ── Singleton factory ─────────────────────────────────────────────────────────

_service_instance: VectorService | None = None


def get_vector_service() -> VectorService:
    """FastAPI dependency — returns the process-wide VectorService singleton."""
    global _service_instance
    if _service_instance is None:
        s = get_settings()
        client = get_chroma_client()
        repo = VectorRepository(client=client, collection_name=s.chroma_collection)
        _service_instance = VectorService(repo)
    return _service_instance


def reset_vector_service() -> None:
    """Reset singleton — for test isolation."""
    global _service_instance
    _service_instance = None
