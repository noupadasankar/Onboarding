"""Document processing endpoint — triggers the chunking pipeline.

Endpoints:
  POST /documents/{id}/process   Run the full chunk pipeline; returns a summary.
  GET  /documents/{id}/chunks    List all chunks for a processed document.
"""
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import RequestContext, authenticated_request
from app.rag.chunk_pipeline import ChunkPipeline
from app.schemas.chunk import ChunkResponse, ProcessingSummary
from app.services.chunk_service import ChunkService, ChunkingConfig, get_chunk_service
from app.services.document_service import DocumentService, get_document_service

router = APIRouter(tags=["processing"])


@router.post(
    "/documents/{document_id}/process",
    response_model=ProcessingSummary,
    status_code=200,
)
async def process_document(
    document_id: str,
    chunk_size: int = 800,
    overlap: int = 100,
    min_tokens: int = 50,
    ctx: RequestContext = Depends(authenticated_request),
    doc_service: DocumentService = Depends(get_document_service),
    chunk_service: ChunkService = Depends(get_chunk_service),
) -> ProcessingSummary:
    """Run the text-cleaning and chunking pipeline on an already-uploaded document.

    The pipeline:
      1. Loads the Document from the document store.
      2. Cleans its text (removes noise, normalises whitespace).
      3. Detects logical sections / headings.
      4. Splits into overlapping token-based chunks.
      5. Validates and filters short / duplicate / gibberish chunks.
      6. Attaches metadata (filename, department, category, section, page).
      7. Stores chunks in memory.
      8. Returns a processing summary.

    Query parameters:
      chunk_size  — Maximum tokens per chunk (default 800).
      overlap     — Token overlap between consecutive chunks (default 100).
      min_tokens  — Minimum tokens for a chunk to be kept (default 50).
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

    config = ChunkingConfig(
        chunk_size=chunk_size,
        overlap=overlap,
        min_tokens=min_tokens,
    )
    pipeline = ChunkPipeline(chunk_service=chunk_service, config=config)
    chunks = await pipeline.run(document)

    return ProcessingSummary.from_chunks(
        document_id=document_id,
        filename=document.filename,
        chunks=chunks,
    )


@router.get(
    "/documents/{document_id}/chunks",
    response_model=list[ChunkResponse],
)
async def list_chunks(
    document_id: str,
    ctx: RequestContext = Depends(authenticated_request),
    doc_service: DocumentService = Depends(get_document_service),
    chunk_service: ChunkService = Depends(get_chunk_service),
) -> list[ChunkResponse]:
    """Return all chunks for a processed document.

    Returns 404 if the document does not exist.
    Returns an empty list if the document exists but has not been processed yet.
    """
    # Confirm the document exists (raises 404 if not)
    doc_service.get(document_id)

    chunks = chunk_service.get_chunks(document_id)
    return [ChunkResponse.from_chunk(c) for c in chunks]
