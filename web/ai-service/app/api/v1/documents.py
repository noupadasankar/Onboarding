"""Document ingestion and retrieval endpoints.

All endpoints require an authenticated internal request (X-Internal-Token +
forwarded user context). Documents are stored in-memory for this increment;
persistence via a database arrives with the chunking + vector-store pipeline.

Endpoints:
  POST   /documents/upload       Upload and parse a document; returns full detail.
  GET    /documents              List all ingested documents (no content).
  GET    /documents/{id}         Retrieve a single document with full content.
  DELETE /documents/{id}         Remove a document from the store.
"""
from fastapi import APIRouter, Depends, File, UploadFile

from app.core.security import RequestContext, authenticated_request
from app.schemas.document import DocumentDetail, DocumentSummary
from app.services.document_service import DocumentService, get_document_service

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentDetail, status_code=201)
async def upload_document(
    file: UploadFile = File(..., description="Document to ingest (PDF, DOCX, TXT, CSV, XLSX)."),
    ctx: RequestContext = Depends(authenticated_request),
    service: DocumentService = Depends(get_document_service),
) -> DocumentDetail:
    """Upload a document and return its parsed content and metadata.

    The file is validated, routed to the correct loader, metadata is enriched,
    and the result is stored in the in-memory document store. Returns the full
    Document (including extracted text) so callers can verify the parse result.
    """
    content = await file.read()
    document = await service.ingest(
        content=content,
        filename=file.filename or "",
        uploaded_by=ctx.user_id,
        department=ctx.department,
    )
    return DocumentDetail.from_document(document)


@router.get("", response_model=list[DocumentSummary])
async def list_documents(
    ctx: RequestContext = Depends(authenticated_request),
    service: DocumentService = Depends(get_document_service),
) -> list[DocumentSummary]:
    """Return all ingested documents without content (bandwidth-friendly list view)."""
    return [DocumentSummary.from_document(doc) for doc in service.list_all()]


@router.get("/{document_id}", response_model=DocumentDetail)
async def get_document(
    document_id: str,
    ctx: RequestContext = Depends(authenticated_request),
    service: DocumentService = Depends(get_document_service),
) -> DocumentDetail:
    """Return a single document including its full extracted content."""
    document = service.get(document_id)
    return DocumentDetail.from_document(document)


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: str,
    ctx: RequestContext = Depends(authenticated_request),
    service: DocumentService = Depends(get_document_service),
) -> None:
    """Remove a document from the in-memory store."""
    service.delete(document_id)
