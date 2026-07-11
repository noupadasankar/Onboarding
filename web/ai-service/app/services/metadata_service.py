"""Metadata enrichment service.

Called by DocumentService after a loader returns a Document. Merges
system-level metadata (word count, character count, extension) and HR
context (department, inferred category) into document.metadata so that
downstream consumers have a single enriched dict to work with.

The loaders themselves capture only format-specific metadata (page count,
sheet names, encoding, etc.); this service adds the cross-format fields
that apply regardless of file type.
"""
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.models.document import Document
from app.utils.file_utils import get_extension, resolve_mime_type
from app.utils.metadata import clean_metadata


class MetadataService:
    """Enriches a loader-produced Document with system and HR metadata."""

    def enrich(
        self,
        document: Document,
        content: bytes,
        department: str | None = None,
    ) -> Document:
        """Merge additional metadata into *document* in place and return it.

        Args:
            document: Document returned by a loader (already carries
                      format-specific metadata populated by the loader).
            content: Original raw bytes of the upload (used for size checks).
            department: HR department from the authenticated request context.

        Returns:
            The same Document instance with enriched metadata.
        """
        ext = get_extension(document.filename)

        extra: dict[str, Any] = {
            # ── Cross-format fields ──────────────────────────────────────────
            "extension": ext,
            "mime_type": resolve_mime_type(document.filename),
            "file_size_bytes": len(content),
            "word_count": len(document.content.split()) if document.content.strip() else 0,
            "char_count": len(document.content),
            "enriched_at": datetime.now(timezone.utc).isoformat(),
            # ── HR context ───────────────────────────────────────────────────
            "category": self._infer_category(document.filename),
        }

        if department:
            extra["department"] = department

        document.metadata.update(clean_metadata(extra))
        return document

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _infer_category(filename: str) -> str:
        """Guess the HR document category from the filename stem.

        Returns one of: policy | leave | compensation | faq | onboarding | general.
        """
        stem = Path(filename).stem.lower().replace("_", " ").replace("-", " ")
        if any(kw in stem for kw in ("handbook", "policy", "code", "conduct")):
            return "policy"
        if any(kw in stem for kw in ("leave", "holiday", "calendar", "vacation")):
            return "leave"
        if any(kw in stem for kw in ("salary", "grade", "compensation", "pay")):
            return "compensation"
        if any(kw in stem for kw in ("faq", "question", "answer")):
            return "faq"
        if any(kw in stem for kw in ("onboard", "orientation", "induction")):
            return "onboarding"
        return "general"


# ── Module-level singleton ─────────────────────────────────────────────────────
metadata_service = MetadataService()
