"""Chunk service — orchestrates the text-to-chunks pipeline.

Responsibilities:
  1. Clean the document's raw text via TextCleaner.
  2. Detect section boundaries via SectionDetector.
  3. Generate overlapping token-based chunks via TokenChunker.
  4. Validate and filter chunks via ChunkValidator.
  5. Attach metadata via MetadataBuilder.
  6. Store chunks in-memory and return the list.

The service is stateful (in-memory store) so previously-processed chunks
are retrievable by document_id until the process restarts. A database-backed
store arrives in Increment 6 alongside the vector store.

Usage::

    from app.services.chunk_service import get_chunk_service
    chunks = await chunk_service.process(document)
"""
import time
from dataclasses import dataclass

from app.chunking.cleaner import TextCleaner
from app.chunking.metadata_builder import MetadataBuilder
from app.chunking.section_detector import SectionDetector
from app.chunking.token_chunker import TokenChunker
from app.chunking.validator import ChunkValidator
from app.core.logging import get_logger
from app.models.chunk import Chunk
from app.models.document import Document

_log = get_logger()


@dataclass
class ChunkingConfig:
    """Configuration for a chunking run."""

    chunk_size: int = 800
    """Maximum tokens per chunk."""

    overlap: int = 100
    """Token overlap between consecutive chunks."""

    min_tokens: int = 50
    """Minimum tokens for a chunk to be kept."""

    remove_duplicates: bool = True
    """Whether to deduplicate identical chunks."""


class ChunkService:
    """In-memory chunk store + chunking pipeline orchestrator.

    All chunk data lives in ``_store`` (keyed by document_id) until the
    process exits. A later increment will persist chunks to ChromaDB.
    """

    def __init__(self) -> None:
        # document_id → list of Chunk objects
        self._store: dict[str, list[Chunk]] = {}

    # ── Ingestion ─────────────────────────────────────────────────────────────

    async def process(
        self,
        document: Document,
        config: ChunkingConfig | None = None,
    ) -> list[Chunk]:
        """Run the full chunking pipeline on *document*.

        Steps:
          1. Clean text.
          2. Detect sections.
          3. Generate token-based overlapping chunks.
          4. Validate and filter.
          5. Attach metadata.
          6. Store and return.

        Args:
            document: The Document produced by Increment 3's loader pipeline.
            config: Optional chunking configuration. Defaults to
                :class:`ChunkingConfig` with 800/100/50 settings.

        Returns:
            List of validated, metadata-rich :class:`Chunk` objects.
        """
        cfg = config or ChunkingConfig()
        doc_id = document.document_id

        _log.info(
            "chunk_pipeline_started",
            document_id=doc_id,
            filename=document.filename,
            content_length=len(document.content),
        )
        t0 = time.monotonic()

        # 1 — Clean
        cleaner = TextCleaner()
        cleaned = cleaner.clean(document.content)
        _log.info("chunk_text_cleaned", document_id=doc_id, cleaned_length=len(cleaned))

        if not cleaned.strip():
            _log.warning("chunk_pipeline_empty_content", document_id=doc_id)
            self._store[doc_id] = []
            return []

        # 2 — Detect sections
        detector = SectionDetector()
        section_blocks = detector.assign_sections(cleaned)
        _log.info(
            "chunk_sections_detected",
            document_id=doc_id,
            section_count=len(section_blocks),
        )

        # 3 — Generate raw chunks
        chunker = TokenChunker(chunk_size=cfg.chunk_size, overlap=cfg.overlap)
        raw_chunks = chunker.chunk_sections(section_blocks)
        _log.info("chunk_raw_generated", document_id=doc_id, count=len(raw_chunks))

        # 4 — Validate and filter
        validator = ChunkValidator(
            min_tokens=cfg.min_tokens,
            remove_duplicates=cfg.remove_duplicates,
        )
        valid_raw = validator.validate_all(raw_chunks)
        discarded = len(raw_chunks) - len(valid_raw)
        _log.info(
            "chunk_validation_complete",
            document_id=doc_id,
            kept=len(valid_raw),
            discarded=discarded,
        )

        # 5 — Attach metadata
        builder = MetadataBuilder(document)
        chunks = builder.build_all(valid_raw)

        # 6 — Store and return
        self._store[doc_id] = chunks
        elapsed_ms = round((time.monotonic() - t0) * 1000, 2)
        _log.info(
            "chunk_pipeline_complete",
            document_id=doc_id,
            chunks_created=len(chunks),
            elapsed_ms=elapsed_ms,
        )

        return chunks

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def get_chunks(self, document_id: str) -> list[Chunk]:
        """Return all chunks for *document_id*, or an empty list if not processed."""
        return self._store.get(document_id, [])

    def has_chunks(self, document_id: str) -> bool:
        """Return True if *document_id* has already been processed."""
        return document_id in self._store

    def delete_chunks(self, document_id: str) -> int:
        """Remove stored chunks for *document_id*.

        Returns:
            Number of chunks deleted (0 if none were stored).
        """
        removed = self._store.pop(document_id, [])
        count = len(removed)
        if count:
            _log.info("chunk_store_deleted", document_id=document_id, count=count)
        return count

    def list_processed(self) -> list[str]:
        """Return all document IDs that have processed chunks."""
        return list(self._store.keys())


# ── Singleton + FastAPI dependency ────────────────────────────────────────────
_service = ChunkService()


def get_chunk_service() -> ChunkService:
    """FastAPI dependency — returns the process-wide ChunkService singleton."""
    return _service
