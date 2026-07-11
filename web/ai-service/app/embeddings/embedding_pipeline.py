"""Embedding pipeline — end-to-end Chunk → EmbeddedChunk orchestration.

Thin wrapper around EmbeddingService that adds:
  * Provider instantiation via EmbeddingFactory (reads settings by default).
  * Optional JSON debug export to ``data/embeddings/``.
  * Centralised logging.

Usage::

    pipeline = EmbeddingPipeline()                  # uses EMBEDDING_PROVIDER from settings
    pipeline = EmbeddingPipeline(provider_name="local")  # explicit provider
    embedded = await pipeline.run(chunks)
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger
from app.embeddings.embedding_factory import EmbeddingFactory
from app.embeddings.embedding_service import EmbeddingConfig, EmbeddingService
from app.embeddings.providers.base_provider import BaseEmbeddingProvider
from app.models.chunk import Chunk
from app.models.embedded_chunk import EmbeddedChunk

_log = get_logger()


class EmbeddingPipeline:
    """Full Chunk-list → EmbeddedChunk-list pipeline.

    Args:
        provider_name: Provider key (``openai``, ``local``, ``voyage``).
            Defaults to ``EMBEDDING_PROVIDER`` setting (default ``local``).
        provider: Pass a pre-built provider to skip factory instantiation
            (useful for testing / dependency injection).
        config: Optional EmbeddingConfig overrides.
    """

    def __init__(
        self,
        provider_name: str | None = None,
        provider: BaseEmbeddingProvider | None = None,
        config: EmbeddingConfig | None = None,
    ) -> None:
        resolved_provider = provider or EmbeddingFactory.create(provider_name)
        self._service = EmbeddingService(resolved_provider)
        self._config = config or EmbeddingConfig()

    # ── Public API ────────────────────────────────────────────────────────────

    async def run(
        self,
        chunks: list[Chunk],
        document_filename: str = "",
    ) -> list[EmbeddedChunk]:
        """Embed *chunks* and optionally export debug JSON.

        Args:
            chunks: Validated Chunk objects from the chunking pipeline.
            document_filename: Used to name the debug export file.

        Returns:
            List of EmbeddedChunk objects.
        """
        if not chunks:
            return []

        embedded = await self._service.embed_chunks(chunks, self._config)

        if embedded:
            self._maybe_export(document_filename, embedded)

        return embedded

    # ── Optional debug export ─────────────────────────────────────────────────

    def _maybe_export(
        self,
        document_filename: str,
        embedded: list[EmbeddedChunk],
    ) -> None:
        """Write embedding vectors to a JSON file if ``embedding_export_dir`` is set."""
        export_dir_str = get_settings().embedding_export_dir
        if not export_dir_str:
            return

        try:
            export_dir = Path(export_dir_str)
            export_dir.mkdir(parents=True, exist_ok=True)

            stem = re.sub(r"[^\w\-]", "_", Path(document_filename or "unknown").stem).lower()
            dest = export_dir / f"{stem}_embeddings.json"

            payload: list[dict[str, Any]] = [
                {
                    "chunk_id": ec.chunk_id,
                    "document_id": ec.document_id,
                    "dimensions": ec.dimensions,
                    "provider": ec.provider,
                    "model": ec.model,
                    "token_count": ec.token_count,
                    "embedding": ec.embedding,
                }
                for ec in embedded
            ]
            dest.write_text(
                json.dumps(
                    {
                        "document_filename": document_filename,
                        "exported_at": datetime.now(timezone.utc).isoformat(),
                        "provider": embedded[0].provider,
                        "model": embedded[0].model,
                        "dimensions": embedded[0].dimensions,
                        "embedding_count": len(embedded),
                        "embeddings": payload,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            _log.info(
                "embedding_export_written",
                path=str(dest),
                count=len(embedded),
            )
        except OSError as exc:
            _log.warning(
                "embedding_export_failed",
                filename=document_filename,
                error=str(exc),
            )
