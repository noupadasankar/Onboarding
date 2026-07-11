"""Document service — orchestrates the ingestion pipeline.

Responsibilities:
  1. Validate the upload via ValidationService (extension, size, duplicates).
  2. Select the correct loader via LoaderFactory.
  3. Parse the file and produce a unified Document.
  4. Enrich document metadata via MetadataService.
  5. Persist to the in-memory store (and optionally to disk).
  6. Expose CRUD operations for the API layer.

The in-memory store (_store) is intentionally simple: it holds documents
for the lifetime of the process. Persistence via a database arrives in a
later increment once the chunking + embedding pipeline is in place.
"""
import time
from pathlib import Path

from fastapi import HTTPException, status

from app.core.config import get_settings
from app.core.logging import get_logger
from app.loaders.exceptions import LoaderError
from app.loaders.factory import LoaderFactory
from app.models.document import Document
from app.services.metadata_service import MetadataService
from app.services.validation_service import ValidationService

_log = get_logger()
_validation = ValidationService()
_metadata = MetadataService()


class DocumentService:
    def __init__(self) -> None:
        self._store: dict[str, Document] = {}

    # ── Ingestion ─────────────────────────────────────────────────────────────

    async def ingest(
        self,
        content: bytes,
        filename: str,
        uploaded_by: str,
        department: str | None = None,
    ) -> Document:
        """Validate, parse, enrich, and store a document. Returns the Document.

        Args:
            content: Raw file bytes from the multipart upload.
            filename: Original filename as provided by the client.
            uploaded_by: User ID from the authenticated request context.
            department: User department from the gateway context (for metadata).

        Returns:
            A fully populated, enriched Document instance.

        Raises:
            HTTPException: Propagated from ValidationService or loader errors.
        """
        _log.info("document_upload_started", filename=filename, size_bytes=len(content))

        # 1. Validate — extension, size, empty check, and duplicate guard
        existing = frozenset(doc.filename for doc in self._store.values())
        ext = _validation.validate(filename, content, existing)
        _log.info("document_upload_validated", filename=filename, extension=ext)

        # 2. Select loader
        loader = LoaderFactory.get_loader(ext)
        _log.info("document_loader_selected", filename=filename, loader=type(loader).__name__)

        # 3. Parse
        t0 = time.monotonic()
        try:
            document = loader.load(content, filename)
        except LoaderError as exc:
            _log.warning("document_parsing_failed", filename=filename, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc

        elapsed_ms = round((time.monotonic() - t0) * 1000, 2)
        _log.info(
            "document_parsing_completed",
            document_id=document.document_id,
            filename=filename,
            content_length=len(document.content),
            elapsed_ms=elapsed_ms,
        )

        # 4. Enrich metadata (word count, category, department, etc.)
        document = _metadata.enrich(document, content, department=department)

        # 5. Attach uploader identity
        document.uploaded_by = uploaded_by

        # 6. Persist original bytes to disk (best-effort, non-blocking)
        self._save_to_disk(filename, content)

        # 7. Store in memory
        self._store[document.document_id] = document

        return document

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def get(self, document_id: str) -> Document:
        """Return a Document by ID or raise 404."""
        doc = self._store.get(document_id)
        if doc is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document '{document_id}' not found.",
            )
        return doc

    def list_all(self) -> list[Document]:
        """Return all stored Documents (no filtering)."""
        return list(self._store.values())

    def delete(self, document_id: str) -> None:
        """Remove a Document from the store or raise 404."""
        if document_id not in self._store:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document '{document_id}' not found.",
            )
        del self._store[document_id]
        _log.info("document_deleted", document_id=document_id)

    # ── Disk persistence (optional) ───────────────────────────────────────────

    @staticmethod
    def _save_to_disk(filename: str, content: bytes) -> None:
        """Save the original file bytes to the configured HR documents directory.

        Best-effort: a failure logs a warning but does NOT abort ingestion.
        Skip entirely when hr_documents_dir is not configured (e.g. in tests).
        """
        data_dir_str = get_settings().hr_documents_dir
        if not data_dir_str:
            return

        try:
            data_dir = Path(data_dir_str)
            data_dir.mkdir(parents=True, exist_ok=True)
            dest = data_dir / filename
            dest.write_bytes(content)
            _log.info("document_saved_to_disk", path=str(dest), size_bytes=len(content))
        except OSError as exc:
            _log.warning("document_disk_save_failed", filename=filename, error=str(exc))


# ── Singleton + FastAPI dependency ────────────────────────────────────────────
_service = DocumentService()


def get_document_service() -> DocumentService:
    """FastAPI dependency — returns the process-wide DocumentService singleton."""
    return _service
