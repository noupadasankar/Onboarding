"""Metadata builder for ChromaDB vector records.

ChromaDB metadata values must be scalar (str, int, float, bool).
This module converts the rich nested metadata on EmbeddedChunk into
a flat dict that ChromaDB can store and filter on.

Rules:
  * Nested dicts / lists are JSON-serialised to a string.
  * None values are replaced with empty string "".
  * datetime values are ISO-formatted strings.
  * All keys are lowercased and stripped.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from app.models.embedded_chunk import EmbeddedChunk


# ── Fixed metadata keys stored on every vector ────────────────────────────────

_ALWAYS_PRESENT = (
    "chunk_id",
    "document_id",
    "filename",
    "file_type",
    "department",
    "category",
    "section",
    "page",
    "token_count",
    "provider",
    "model",
    "dimensions",
    "indexed_at",
    # Versioning — retrieval filters on is_latest to hide superseded versions.
    "is_latest",
    "version",
    # Embedding/LLM provenance — keeps vectors traceable across model switches.
    "embedding_provider",
    "embedding_model",
    "embedding_dimension",
    "llm_provider",
)


def build_chroma_metadata(ec: EmbeddedChunk, indexed_at: str = "") -> dict[str, Any]:
    """Build a flat ChromaDB-compatible metadata dict from *ec*.

    Args:
        ec: The EmbeddedChunk to extract metadata from.
        indexed_at: ISO timestamp string for when indexing happened.

    Returns:
        Flat ``{str: scalar}`` dict suitable for ChromaDB.
    """
    raw = dict(ec.metadata)

    flat: dict[str, Any] = {
        "chunk_id": ec.chunk_id,
        "document_id": ec.document_id,
        "filename": str(raw.get("filename", "")),
        "file_type": str(raw.get("file_type", "")),
        "department": str(raw.get("department", "")),
        "category": str(raw.get("category", "")),
        "section": str(raw.get("section", "") or ""),
        "page": int(raw["page"]) if raw.get("page") is not None else -1,
        "token_count": ec.token_count,
        "provider": ec.provider,
        "model": ec.model,
        "dimensions": ec.dimensions,
        "indexed_at": indexed_at or datetime.utcnow().isoformat(),
        "source": str(raw.get("source", "")),
        "uploaded_by": str(raw.get("uploaded_by", "")),
        # Versioning — bool/int kept native so ChromaDB can filter on them.
        "is_latest": bool(raw.get("is_latest", True)),
        "version": int(raw["version"]) if raw.get("version") is not None else 1,
        # Embedding/LLM provenance (aliases of provider/model for clarity + future
        # cross-provider filtering; safe defaults from the embedded chunk).
        "embedding_provider": ec.provider,
        "embedding_model": ec.model,
        "embedding_dimension": ec.dimensions,
        "llm_provider": str(raw.get("llm_provider", "")),
    }

    # Flatten any remaining metadata keys that aren't already present
    for k, v in raw.items():
        key = k.lower().strip()
        if key in flat:
            continue
        flat[key] = _to_scalar(v)

    return flat


def _to_scalar(value: Any) -> str | int | float | bool:
    """Convert *value* to a ChromaDB-safe scalar."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return value
    if isinstance(value, str):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    # Fallback: JSON-encode nested structures
    try:
        return json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(value)
