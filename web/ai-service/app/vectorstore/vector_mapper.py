"""Vector mapper — converts between EmbeddedChunk / VectorDocument and ChromaDB wire format.

ChromaDB's ``collection.upsert`` and ``collection.get`` use positional
parallel lists (ids, embeddings, documents, metadatas).  This module
handles the conversion so no other layer has to think about it.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.models.embedded_chunk import EmbeddedChunk
from app.models.vector_document import VectorDocument, VectorSearchResult
from app.vectorstore.metadata_builder import build_chroma_metadata


def embedded_chunk_to_upsert_args(
    ec: EmbeddedChunk,
    text: str,
) -> dict[str, Any]:
    """Return the kwargs dict for ``collection.upsert`` for a single EmbeddedChunk.

    Args:
        ec: The embedded chunk to persist.
        text: Original chunk text (stored as the ChromaDB document string).

    Returns:
        Dict with ``ids``, ``embeddings``, ``documents``, ``metadatas`` — each
        a single-element list as required by chromadb's API.
    """
    indexed_at = datetime.now(timezone.utc).isoformat()
    return {
        "ids": [ec.chunk_id],
        "embeddings": [ec.embedding],
        "documents": [text],
        "metadatas": [build_chroma_metadata(ec, indexed_at=indexed_at)],
    }


def batch_to_upsert_args(
    items: list[tuple[EmbeddedChunk, str]],
) -> dict[str, Any]:
    """Build a single batch upsert payload from a list of (EmbeddedChunk, text) pairs."""
    indexed_at = datetime.now(timezone.utc).isoformat()
    ids, embeddings, documents, metadatas = [], [], [], []
    for ec, text in items:
        ids.append(ec.chunk_id)
        embeddings.append(ec.embedding)
        documents.append(text)
        metadatas.append(build_chroma_metadata(ec, indexed_at=indexed_at))
    return {
        "ids": ids,
        "embeddings": embeddings,
        "documents": documents,
        "metadatas": metadatas,
    }


def chroma_result_to_vector_documents(result: dict[str, Any]) -> list[VectorDocument]:
    """Convert the dict returned by ``collection.get(include=[...])`` to VectorDocument list."""
    ids = result.get("ids") or []
    embeddings = result.get("embeddings") or [None] * len(ids)
    documents = result.get("documents") or [""] * len(ids)
    metadatas = result.get("metadatas") or [{}] * len(ids)

    out = []
    for chunk_id, emb, doc, meta in zip(ids, embeddings, documents, metadatas):
        out.append(
            VectorDocument(
                chunk_id=chunk_id,
                document_id=str(meta.get("document_id", "")),
                embedding=list(emb) if emb else [],
                text=doc or "",
                metadata=dict(meta) if meta else {},
            )
        )
    return out


def chroma_query_to_search_results(
    query_result: dict[str, Any],
) -> list[VectorSearchResult]:
    """Convert the dict returned by ``collection.query(...)`` to VectorSearchResult list.

    ChromaDB returns nested lists (one per query vector).  We always query
    with a single vector, so we unwrap the first item.
    """
    ids_nested = query_result.get("ids") or [[]]
    docs_nested = query_result.get("documents") or [[]]
    metas_nested = query_result.get("metadatas") or [[]]
    dists_nested = query_result.get("distances") or [[]]

    ids = ids_nested[0] if ids_nested else []
    docs = docs_nested[0] if docs_nested else []
    metas = metas_nested[0] if metas_nested else []
    dists = dists_nested[0] if dists_nested else []

    results = []
    for chunk_id, doc, meta, dist in zip(ids, docs, metas, dists):
        # Chroma returns cosine *distance* (0=identical, 2=opposite) when using
        # hnsw:space=cosine.  Convert to similarity: score = 1 - distance/2
        score = float(1.0 - (dist / 2.0)) if dist is not None else 0.0
        results.append(
            VectorSearchResult(
                chunk_id=chunk_id,
                document_id=str(meta.get("document_id", "")),
                text=doc or "",
                score=round(score, 6),
                metadata=dict(meta) if meta else {},
            )
        )
    return results
