"""Vectorstore API endpoints.

Endpoints:
  POST /documents/index                    Index document from storage path (called by Node gateway)
  POST /documents/{document_id}/index      Run full pipeline on already-uploaded document
  GET  /vectorstore/health                 Collection health check
  GET  /vectorstore/count                  Collection statistics
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import RequestContext, authenticated_request
from app.embeddings.embedding_pipeline import EmbeddingPipeline
from app.embeddings.embedding_service import EmbeddingConfig
from app.embeddings.providers.local_provider import LocalProvider
from app.models.chunk import Chunk
from app.rag.chunk_pipeline import ChunkPipeline
from app.schemas.vector import (
    IndexDocumentByPathRequest,
    IndexDocumentByPathResponse,
    IndexingSummary,
    VectorCountResponse,
    VectorHealthResponse,
)
from app.services.chunk_service import ChunkService, ChunkingConfig, get_chunk_service
from app.services.document_service import DocumentService, get_document_service
from app.services.vector_service import VectorService, get_vector_service
from app.core.config import get_settings
from app.core.logging import get_logger

_log = get_logger()

router = APIRouter(tags=["vectorstore"])


@router.post(
    "/documents/index",
    response_model=IndexDocumentByPathResponse,
    status_code=200,
)
async def index_document_by_path(
    req: IndexDocumentByPathRequest,
    ctx: RequestContext = Depends(authenticated_request),
    doc_service: DocumentService = Depends(get_document_service),
    chunk_service: ChunkService = Depends(get_chunk_service),
    vector_service: VectorService = Depends(get_vector_service),
) -> IndexDocumentByPathResponse:
    """Index a document from a storage path — called by the Node gateway.

    Reads the file from *storage_path*, runs the full chunk → embed → store
    pipeline, and returns chunk/vector counts.  Uses the backend's document UUID
    as the ChromaDB document identifier so vector deletion stays consistent.
    """
    path = Path(req.storage_path)
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found at storage path: {req.storage_path}",
        )

    content = path.read_bytes()
    _log.info(
        "index_by_path_start",
        document_id=req.document_id,
        filename=req.filename,
        size_bytes=len(content),
    )

    # Ingest into the in-memory doc store so the chunk pipeline can access the text
    document = await doc_service.ingest(
        content=content,
        filename=req.filename,
        uploaded_by=ctx.user_id,
        department=req.department,
    )
    # Override the AI-service UUID with the backend's UUID so ChromaDB vector
    # deletion (DELETE /documents/{id}/vectors) maps back to the right record.
    document.document_id = req.document_id

    # Attach versioning + provenance so every chunk inherits it into the vector
    # metadata. is_latest lets retrieval exclude superseded versions; the rest is
    # traceability (who/when/where) that makes future filtering trivial.
    document.metadata.update(
        {
            "is_latest": req.is_latest,
            "version": req.version,
            "department_id": req.department_id or "",
            "document_uuid": req.document_id,
            "uploaded_by": req.uploaded_by or ctx.user_id,
            "uploaded_at": req.uploaded_at or "",
            "document_status": req.document_status or "INDEXED",
            "mime_type": req.mime_type,
            "storage_path": req.storage_path,
        }
    )

    # ── Chunk ─────────────────────────────────────────────────────────────────
    s = get_settings()
    chunk_config = ChunkingConfig(chunk_size=800, overlap=100, min_tokens=50)
    chunk_pl = ChunkPipeline(chunk_service=chunk_service, config=chunk_config)
    chunks: list[Chunk] = await chunk_pl.run(document)

    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Document produced no valid chunks after cleaning and validation.",
        )

    # ── Embed ─────────────────────────────────────────────────────────────────
    embed_config = EmbeddingConfig(
        batch_size=s.embedding_batch_size,
        enable_cache=True,
    )
    embed_pl = EmbeddingPipeline(config=embed_config)
    embedded = await embed_pl.run(chunks, document_filename=req.filename)

    if not embedded:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Embedding pipeline returned no vectors.",
        )

    # ── Store ─────────────────────────────────────────────────────────────────
    chunk_texts: dict[str, str] = {c.chunk_id: c.text for c in chunks}
    indexed = vector_service.index(embedded, chunk_texts)

    _log.info(
        "index_by_path_complete",
        document_id=req.document_id,
        chunks=indexed,
    )

    return IndexDocumentByPathResponse(
        status="indexed",
        chunk_count=indexed,
        vector_count=indexed,
        ai_document_id=req.document_id,
    )


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
