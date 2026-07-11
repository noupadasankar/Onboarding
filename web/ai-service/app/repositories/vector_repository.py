"""Vector repository — the only layer that touches ChromaDB directly.

All other layers (VectorService, API) depend on this interface,
never on chromadb itself.  Swapping ChromaDB for Qdrant or Weaviate
only requires a new repository implementation.

Public methods mirror the spec:
  upsert_batch()     — insert-or-update a list of EmbeddedChunks
  delete_document()  — remove all chunks belonging to a document_id
  delete_chunk()     — remove a single chunk by chunk_id
  get_by_document()  — retrieve all VectorDocuments for a document_id
  count()            — total number of vectors in the collection
  search()           — nearest-neighbour search (Increment 7 will use this)
  health()           — True if the collection is reachable
"""
from __future__ import annotations

from typing import Any

from app.core.logging import get_logger
from app.models.embedded_chunk import EmbeddedChunk
from app.models.vector_document import CollectionStats, VectorDocument, VectorSearchResult
from app.vectorstore.chroma_client import ChromaClient
from app.vectorstore.collections import CollectionManager
from app.vectorstore.search_filters import SearchFilters
from app.vectorstore.vector_mapper import (
    batch_to_upsert_args,
    chroma_query_to_search_results,
    chroma_result_to_vector_documents,
)

_log = get_logger()

_UPSERT_BATCH = 500   # max items per single chroma upsert call


class VectorRepository:
    """ChromaDB-backed repository for EmbeddedChunk persistence.

    Args:
        client: Shared ChromaClient.
        collection_name: Target collection (e.g. ``hr_documents``).
    """

    def __init__(self, client: ChromaClient, collection_name: str) -> None:
        self._manager = CollectionManager(client)
        self._collection_name = collection_name
        self._coll = self._manager.get_or_create(collection_name)

    # ── Write operations ───────────────────────────────────────────────────────

    def upsert_batch(
        self,
        items: list[tuple[EmbeddedChunk, str]],
    ) -> int:
        """Upsert a batch of ``(EmbeddedChunk, text)`` pairs into the collection.

        ChromaDB upsert is idempotent on ID — it updates if the ID exists,
        inserts otherwise.

        Args:
            items: List of (embedded_chunk, original_text) tuples.

        Returns:
            Number of records upserted.
        """
        if not items:
            return 0

        total = 0
        for start in range(0, len(items), _UPSERT_BATCH):
            batch = items[start : start + _UPSERT_BATCH]
            args = batch_to_upsert_args(batch)
            self._coll.upsert(**args)
            total += len(batch)
            _log.info(
                "vector_upsert_batch",
                collection=self._collection_name,
                count=len(batch),
            )

        return total

    def delete_document(self, document_id: str) -> int:
        """Delete all vectors whose ``document_id`` metadata matches.

        Returns:
            Number of chunks deleted (0 if none found).
        """
        where = SearchFilters().by_document(document_id).build()
        # Fetch IDs first, then delete — Chroma requires explicit IDs for delete
        existing = self._coll.get(where=where, include=[])
        ids = existing.get("ids") or []
        if ids:
            self._coll.delete(ids=ids)
            _log.info(
                "vector_delete_document",
                document_id=document_id,
                deleted=len(ids),
            )
        return len(ids)

    def delete_chunk(self, chunk_id: str) -> bool:
        """Delete a single vector by chunk_id.

        Returns:
            True if deleted, False if not found.
        """
        existing = self._coll.get(ids=[chunk_id], include=[])
        if not (existing.get("ids") or []):
            return False
        self._coll.delete(ids=[chunk_id])
        _log.info("vector_delete_chunk", chunk_id=chunk_id)
        return True

    # ── Read operations ───────────────────────────────────────────────────────

    def get_by_document(self, document_id: str) -> list[VectorDocument]:
        """Return all stored VectorDocuments for *document_id*."""
        where = SearchFilters().by_document(document_id).build()
        result = self._coll.get(
            where=where,
            include=["embeddings", "documents", "metadatas"],
        )
        return chroma_result_to_vector_documents(result)

    def get_chunk(self, chunk_id: str) -> VectorDocument | None:
        """Return the VectorDocument for *chunk_id*, or None if not found."""
        result = self._coll.get(
            ids=[chunk_id],
            include=["embeddings", "documents", "metadatas"],
        )
        docs = chroma_result_to_vector_documents(result)
        return docs[0] if docs else None

    def exists(self, chunk_id: str) -> bool:
        """Return True if *chunk_id* is already stored in the collection."""
        result = self._coll.get(ids=[chunk_id], include=[])
        return bool(result.get("ids"))

    def count(self) -> int:
        """Return total number of vectors in the collection."""
        return self._coll.count()

    def get_all_text(
        self,
        where: "dict | None" = None,
    ) -> "list[dict]":
        """Return all chunk texts and metadata for BM25 index construction.

        Does NOT include embeddings (large vectors not needed for keyword search).
        Safe to call to build an in-memory BM25 index.

        Args:
            where: Optional ChromaDB metadata filter dict.

        Returns:
            List of dicts with keys: chunk_id, text, document_id, metadata.
        """
        kwargs: dict = {"include": ["documents", "metadatas"]}
        if where:
            kwargs["where"] = where

        result = self._coll.get(**kwargs)
        ids = result.get("ids") or []
        texts = result.get("documents") or []
        metas = result.get("metadatas") or []

        return [
            {
                "chunk_id": chunk_id,
                "text": text or "",
                "document_id": str((meta or {}).get("document_id", "")),
                "metadata": meta or {},
            }
            for chunk_id, text, meta in zip(ids, texts, metas)
            if text
        ]

    def unique_document_ids(self) -> list[str]:
        """Return a deduplicated list of document_ids stored in the collection."""
        result = self._coll.get(include=["metadatas"])
        metas = result.get("metadatas") or []
        seen: set[str] = set()
        for m in metas:
            doc_id = (m or {}).get("document_id", "")
            if doc_id:
                seen.add(str(doc_id))
        return sorted(seen)

    # ── Search ────────────────────────────────────────────────────────────────

    def search(
        self,
        query_embedding: list[float],
        n_results: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[VectorSearchResult]:
        """Find the *n_results* nearest neighbours of *query_embedding*.

        Args:
            query_embedding: The query vector (same dimensionality as stored).
            n_results: Maximum results to return.
            where: Optional ChromaDB metadata filter dict.

        Returns:
            Ordered list of VectorSearchResult (highest similarity first).
        """
        kwargs: dict[str, Any] = {
            "query_embeddings": [query_embedding],
            "n_results": min(n_results, self.count() or 1),
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            kwargs["where"] = where

        result = self._coll.query(**kwargs)
        return chroma_query_to_search_results(result)

    # ── Health / stats ────────────────────────────────────────────────────────

    def health(self) -> bool:
        """Return True if the collection can be queried."""
        try:
            self._coll.count()
            return True
        except Exception:
            return False

    def stats(self, embedding_model: str = "", embedding_dimensions: int = 0) -> CollectionStats:
        """Return collection-level statistics."""
        total = self.count()
        unique_docs = len(self.unique_document_ids())
        return CollectionStats(
            collection_name=self._collection_name,
            total_chunks=total,
            unique_documents=unique_docs,
            embedding_model=embedding_model,
            embedding_dimensions=embedding_dimensions,
        )
