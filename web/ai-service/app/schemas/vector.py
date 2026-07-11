"""Response schemas for vector store endpoints."""
from __future__ import annotations

from pydantic import BaseModel


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
