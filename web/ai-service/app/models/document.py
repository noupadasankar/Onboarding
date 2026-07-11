"""Unified internal document model.

Every loader — regardless of file format — produces a Document. This model is
the contract between the ingestion pipeline (loaders) and downstream consumers
(chunking in Increment 4, embeddings in Increment 5, RAG in Increment 7).

Never expose this model directly as an API response; use the schemas in
app/schemas/document.py to project the fields the client needs.
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class FileType(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    CSV = "csv"
    XLSX = "xlsx"


class Document(BaseModel):
    """Unified document representation produced by every loader."""

    document_id: str = Field(default_factory=lambda: str(uuid4()))
    filename: str
    file_type: FileType
    mime_type: str
    content: str
    metadata: dict[str, Any]
    page_count: int | None = None
    source: str
    size_bytes: int
    uploaded_by: str = ""
    uploaded_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
