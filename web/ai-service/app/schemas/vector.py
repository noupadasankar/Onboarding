"""Response schemas for vector store endpoints."""
from __future__ import annotations

from pydantic import BaseModel


class IndexDocumentByPathRequest(BaseModel):
    document_id: str
    filename: str
    storage_path: str
    department: str | None = None
    mime_type: str
    size_bytes: int
    # Versioning — the document being indexed is always the current latest.
    # Defaulted so older gateway callers that omit them still work.
    version: int = 1
    is_latest: bool = True
    # Provenance — persisted into vector metadata for traceability/filtering.
    department_id: str | None = None
    uploaded_by: str | None = None
    uploaded_at: str | None = None
    document_status: str | None = None


class IndexDocumentByPathResponse(BaseModel):
    status: str = "indexed"
    chunk_count: int | None = None
    vector_count: int | None = None
    ai_document_id: str | None = None


class VectorHealthResponse(BaseModel):
    status: str          # "healthy" | "unavailable"
    database: str = "ChromaDB"
    collection: str = ""
    total_chunks: int = 0
    unique_documents: int = 0


class IndexingSummary(BaseModel):
    success: bool
    document_id: str
    filename: str
    chunks_indexed: int
    provider: str = ""
    model: str = ""


class VectorCountResponse(BaseModel):
    collection: str
    total_chunks: int
    unique_documents: int
