"""Dedicated validation service for document uploads.

Centralises all upload gate-keeping so the document service delegates
to a single method. Wraps the lower-level utility checks from
app.utils.file_utils and extends them with duplicate detection.

Validation order (Increment 3 spec, Step 2):
  1. Filename present and not a dotfile
  2. Filename length <= 255 chars
  3. Extension in supported set
  4. File is not empty
  5. File does not exceed the 20 MB size limit
  6. Filename not a duplicate of an already-stored document
"""
from fastapi import HTTPException, status

from app.utils.file_utils import (
    MAX_FILENAME_LENGTH,
    MAX_UPLOAD_SIZE_BYTES,
    SUPPORTED_EXTENSIONS,
    get_extension,
)


class ValidationService:
    """Validates document uploads before they reach the loader pipeline."""

    def validate(
        self,
        filename: str,
        content: bytes,
        existing_filenames: frozenset[str] | None = None,
    ) -> str:
        """Run all validation checks and return the file extension on success.

        Args:
            filename: Original client filename.
            content: Raw upload bytes.
            existing_filenames: Filenames already in the store; checked for
                                duplicates when provided.

        Returns:
            Lower-case extension without the leading dot (e.g. ``"pdf"``).

        Raises:
            HTTPException 400: Bad filename or empty file.
            HTTPException 409: Duplicate filename.
            HTTPException 413: File exceeds the size limit.
            HTTPException 415: Unsupported file type.
        """
        self._check_filename(filename)
        ext = self._check_extension(filename)
        self._check_not_empty(content)
        self._check_size(content)
        if existing_filenames is not None:
            self._check_duplicate(filename, existing_filenames)
        return ext

    # ── Individual checks ─────────────────────────────────────────────────────

    @staticmethod
    def _check_filename(filename: str) -> None:
        if not filename or not filename.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Filename is required.",
            )
        if filename.startswith("."):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Hidden files (dotfiles) are not accepted.",
            )
        if len(filename) > MAX_FILENAME_LENGTH:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Filename must be {MAX_FILENAME_LENGTH} characters or fewer.",
            )

    @staticmethod
    def _check_extension(filename: str) -> str:
        ext = get_extension(filename)
        if ext not in SUPPORTED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=(
                    f"File type '.{ext}' is not supported. "
                    f"Accepted types: {sorted(SUPPORTED_EXTENSIONS)}."
                ),
            )
        return ext

    @staticmethod
    def _check_not_empty(content: bytes) -> None:
        if len(content) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty.",
            )

    @staticmethod
    def _check_size(content: bytes) -> None:
        if len(content) > MAX_UPLOAD_SIZE_BYTES:
            limit_mb = MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size exceeds the {limit_mb} MB limit.",
            )

    @staticmethod
    def _check_duplicate(filename: str, existing: frozenset[str]) -> None:
        if filename in existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"A document named '{filename}' already exists. "
                    "Delete it first or upload with a different name."
                ),
            )


# ── Module-level singleton ─────────────────────────────────────────────────────
validation_service = ValidationService()
