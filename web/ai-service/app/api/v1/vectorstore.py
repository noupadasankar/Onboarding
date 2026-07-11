"""Vectorstore API endpoints.

Endpoints:
  POST /documents/{document_id}/index      Run full pipeline → store in Chroma
  GET  /vectorstore/health                 Collection health check
  GET  /vectorstore/count                  Collection statistics
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import RequestContext, authenticated_request
from app.embeddings.embedding_pipeline import EmbeddingPipeline
from app.embeddings.embedding_service import EmbeddingConfig
from app.embeddings.providers.local_provider import LocalProvider
from app.models.chunk import Chunk
from app.rag.chunk_pipeline import ChunkPipeline
from app.schemas.vector import IndexingSummary, VectorCountResponse, VectorHealthResponse
from app.services.chunk_service import ChunkService, ChunkingConfig, get_chunk_service
from app.services.document_service import DocumentService, get_document_service
from app.services.vector_service import VectorService, get_vector_service
from app.core.config import get_settings

router = APIRouter(tags=["vectorstore"])


@router.post(
    "/documents/{document_id}/index",
    response_model=IndexingSummary,
    status_code=200,
)
async def index_document(
    document_id: str,
    chunk_size: int = 800,
    overlap: int = 100,
    min_tokens: int = 50,
    reindex: bool = False,
    ctx: RequestContext = Depends(authenticated_request),
    doc_service: DocumentService = Depends(get_document_service),
    chunk_service: ChunkService = Depends(get_chunk_service),
    vector_service: VectorService = Depends(get_vector_service),
) -> IndexingSummary:
    """Run the full Document → Chunk → Embed → ChromaDB pipeline.

    Query parameters:
      chunk_size  — Maximum tokens per chunk (default 800).
      overlap     — Token overlap between chunks (default 100).
      min_tokens  — Minimum tokens to keep a chunk (default 50).
      reindex     — If True, deletes existing vectors before indexing (default False).
    """
    if chunk_size < 100 or chunk_size > 4096:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="chunk_size must be between 100 and 4096.",
        )
    if overlap >= chunk_size:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="overlap must be strictly less than chunk_size.",
        )

    document = doc_service.get(document_id)

    # ── 1. Chunk ──────────────────────────────────────────────────────────────
    chunk_config = ChunkingConfig(
        chunk_size=chunk_size, overlap=overlap, min_tokens=min_tokens
    )
    chunk_pl = ChunkPipeline(chunk_service=chunk_service, config=chunk_config)
    chunks: list[Chunk] = await chunk_pl.run(document)

    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Document produced no valid chunks after cleaning and validation.",
        )

    # ── 2. Embed ──────────────────────────────────────────────────────────────
    s = get_settings()
    embed_config = EmbeddingConfig(
        batch_size=s.embedding_batch_size,
        enable_cache=True,
    )
    embed_pl = EmbeddingPipeline(config=embed_config)
    embedded = await embed_pl.run(chunks, document_filename=document.filename)

    if not embedded:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Embedding pipeline returned no vectors.",
        )

    # ── 3. Store ──────────────────────────────────────────────────────────────
    chunk_texts: dict[str, str] = {c.chunk_id: c.text for c in chunks}

    if reindex:
        indexed = vector_service.reindex_document(document_id, embedded, chunk_texts)
    else:
        indexed = vector_service.index(embedded, chunk_texts)

    return IndexingSummary(
        success=True,
        document_id=document_id,
        filename=document.filename,
        chunks_indexed=indexed,
        provider=embedded[0].provider,
        model=embedded[0].model,
    )


@router.delete("/documents/{document_id}/vectors", status_code=200)
async def delete_document_vectors(
    document_id: str,
    ctx: RequestContext = Depends(authenticated_request),
    vector_service: VectorService = Depends(get_vector_service),
) -> dict:
    """Delete all ChromaDB vectors for *document_id*.

    Called by the Node backend when a new version of a document supersedes an
    older one.  The Postgres record has already been marked SUPERSEDED; this
    endpoint removes the stale chunks so they cannot appear in future searches.

    Returns:
        ``{"document_id": ..., "vectors_deleted": N}``
    """
    deleted = vector_service.delete_document(document_id)
    return {"document_id": document_id, "vectors_deleted": deleted}


@router.get("/vectorstore/health", response_model=VectorHealthResponse)
async def vectorstore_health(
    ctx: RequestContext = Depends(authenticated_request),
    vector_service: VectorService = Depends(get_vector_service),
) -> VectorHealthResponse:
    """Return ChromaDB collection health status."""
    s = get_settings()
    healthy = vector_service.health()
    if healthy:
        st = vector_service.stats()
        return VectorHealthResponse(
            status="healthy",
            collection=s.chroma_collection,
            total_chunks=st.total_chunks,
            unique_documents=st.unique_documents,
        )
    return VectorHealthResponse(
        status="unavailable",
        collection=s.chroma_collection,
    )


@router.get("/vectorstore/count", response_model=VectorCountResponse)
async def vectorstore_count(
    ctx: RequestContext = Depends(authenticated_request),
    vector_service: VectorService = Depends(get_vector_service),
) -> VectorCountResponse:
    """Return total chunk and document counts in the collection."""
    s = get_settings()
    st = vector_service.stats()
    return VectorCountResponse(
        collection=s.chroma_collection,
        total_chunks=st.total_chunks,
        unique_documents=st.unique_documents,
    )
