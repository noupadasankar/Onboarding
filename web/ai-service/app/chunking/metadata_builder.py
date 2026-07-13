"""Chunk metadata builder.

Attaches document-level metadata (department, filename, file type, source)
plus chunk-specific metadata (position, section) to each raw chunk,
producing a fully-populated :class:`~app.models.chunk.Chunk` object.

This is the final step in the chunking pipeline before the chunk list is
returned to the caller.
"""
from __future__ import annotations

from typing import Any

from app.chunking.token_chunker import RawChunk
from app.models.chunk import Chunk
from app.models.document import Document


class MetadataBuilder:
    """Converts :class:`RawChunk` objects into fully-populated :class:`Chunk` objects.

    Args:
        document: The parent document; its metadata is inherited by all chunks.
    """

    def __init__(self, document: Document) -> None:
        self._document = document
        self._inherited: dict[str, Any] = self._extract_inherited_fields()

    # ── Public API ────────────────────────────────────────────────────────────

    def build(self, raw: RawChunk, index: int) -> Chunk:
        """Build a :class:`Chunk` from *raw* and attach metadata.

        Args:
            raw: Validated raw chunk from the chunker.
            index: 0-based position in the final chunk list.

        Returns:
            A fully-populated :class:`Chunk` ready for embedding.
        """
        chunk_id = Chunk.build_id(self._document.document_id, index)

        # Merge: inherited doc metadata → chunk-specific fields → raw extra
        metadata: dict[str, Any] = {
            **self._inherited,
            "chunk_index": index,
            "chunk_id": chunk_id,
            **raw.extra_metadata,
        }

        return Chunk(
            chunk_id=chunk_id,
            document_id=self._document.document_id,
            chunk_index=index,
            text=raw.text,
            token_count=raw.token_count,
            page=raw.page,
            section=raw.section or None,
            metadata=metadata,
        )

    def build_all(self, raw_chunks: list[RawChunk]) -> list[Chunk]:
        """Build :class:`Chunk` objects for every item in *raw_chunks*."""
        return [self.build(raw, idx) for idx, raw in enumerate(raw_chunks)]

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _extract_inherited_fields(self) -> dict[str, Any]:
        """Pull the fields from the parent Document that every chunk inherits."""
        doc = self._document
        doc_meta = doc.metadata or {}
        return {
            "filename": doc.filename,
            "file_type": doc.file_type.value,
            "source": doc.source,
            "document_id": doc.document_id,
            # HR-specific context (may be absent on non-HR docs)
            "department": doc_meta.get("department"),
            "category": doc_meta.get("category"),
            # Versioning — defaults keep legacy/re-processed docs retrievable.
            "is_latest": doc_meta.get("is_latest", True),
            "version": doc_meta.get("version", 1),
            # Provenance (traceability + future metadata filtering)
            "department_id": doc_meta.get("department_id", ""),
            "document_uuid": doc_meta.get("document_uuid", doc.document_id),
            "uploaded_by": doc_meta.get("uploaded_by", ""),
            "uploaded_at": doc_meta.get("uploaded_at", ""),
            "document_status": doc_meta.get("document_status", ""),
            "mime_type": doc_meta.get("mime_type", ""),
            "storage_path": doc_meta.get("storage_path", ""),
        }
