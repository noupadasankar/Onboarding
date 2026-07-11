"""Reusable chunk pipeline.

Thin orchestration wrapper around ChunkService that additionally handles
optional JSON export for debugging (Step 10 of the Increment 4 spec).

Usage::

    pipeline = ChunkPipeline()
    chunks = await pipeline.run(document)

The pipeline is stateless; create one per request or share a singleton.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.chunk import Chunk
from app.models.document import Document
from app.services.chunk_service import ChunkService, ChunkingConfig

_log = get_logger()


class ChunkPipeline:
    """End-to-end Document → Chunk-list pipeline.

    Wraps :class:`~app.services.chunk_service.ChunkService` and adds:

    * Optional JSON export to ``data/chunks/hr/<stem>_chunks.json``
      (enabled when ``chunk_export_dir`` is configured in settings).
    * Centralised logging / error surfacing.

    Args:
        chunk_service: Service to delegate chunking to.
        config: Optional chunking configuration overrides.
    """

    def __init__(
        self,
        chunk_service: ChunkService,
        config: ChunkingConfig | None = None,
    ) -> None:
        self._service = chunk_service
        self._config = config or ChunkingConfig()

    # ── Public API ────────────────────────────────────────────────────────────

    async def run(self, document: Document) -> list[Chunk]:
        """Process *document* and return its chunks.

        Args:
            document: Fully loaded and metadata-enriched Document.

        Returns:
            List of validated, metadata-rich :class:`Chunk` objects.
        """
        chunks = await self._service.process(document, self._config)
        if chunks:
            self._maybe_export(document, chunks)
        return chunks

    # ── Optional JSON export ──────────────────────────────────────────────────

    def _maybe_export(self, document: Document, chunks: list[Chunk]) -> None:
        """Write chunks to a JSON file if ``chunk_export_dir`` is configured."""
        export_dir_str = get_settings().chunk_export_dir
        if not export_dir_str:
            return

        try:
            export_dir = Path(export_dir_str)
            export_dir.mkdir(parents=True, exist_ok=True)

            stem = re.sub(r"[^\w\-]", "_", Path(document.filename).stem).lower()
            dest = export_dir / f"{stem}_chunks.json"

            payload: list[dict[str, Any]] = [
                {
                    "chunk_id": c.chunk_id,
                    "chunk_index": c.chunk_index,
                    "page": c.page,
                    "section": c.section,
                    "token_count": c.token_count,
                    "text": c.text,
                }
                for c in chunks
            ]
            dest.write_text(
                json.dumps(
                    {
                        "document_id": document.document_id,
                        "filename": document.filename,
                        "exported_at": datetime.now(timezone.utc).isoformat(),
                        "chunk_count": len(chunks),
                        "chunks": payload,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            _log.info(
                "chunk_export_written",
                path=str(dest),
                chunk_count=len(chunks),
            )
        except OSError as exc:
            _log.warning(
                "chunk_export_failed",
                filename=document.filename,
                error=str(exc),
            )
