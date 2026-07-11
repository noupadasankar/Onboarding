"""Upload validation utilities.

Validation happens at the API boundary before any file bytes reach a loader.
All functions raise HTTPException directly so the endpoint's error shape is
consistent with the rest of the service.
"""
from fastapi import HTTPException, status

# ── Limits ────────────────────────────────────────────────────────────────────
MAX_UPLOAD_SIZE_BYTES: int = 20 * 1024 * 1024  # 20 MB
MAX_FILENAME_LENGTH: int = 255

# ── Allowed types ─────────────────────────────────────────────────────────────
SUPPORTED_EXTENSIONS: frozenset[str] = frozenset({"pdf", "docx", "txt", "csv", "xlsx"})

EXTENSION_MIME_MAP: dict[str, str] = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "txt": "text/plain",
    "csv": "text/csv",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


def get_extension(filename: str) -> str:
    """Return the lower-case extension without a leading dot, or '' if none."""
    parts = filename.rsplit(".", 1)
    return parts[1].lower() if len(parts) == 2 else ""


def resolve_mime_type(filename: str) -> str:
    """Derive the canonical MIME type from the file extension."""
    return EXTENSION_MIME_MAP.get(get_extension(filename), "application/octet-stream")


def validate_upload(filename: str, content: bytes) -> str:
    """Validate a file upload. Returns the extension on success.

    Checks (in order):
      1. Filename is present and not a dotfile.
      2. Filename length.
      3. Extension is supported.
      4. File is not empty.
      5. File does not exceed the size limit.

    Raises:
        HTTPException 400: Empty file or bad filename.
        HTTPException 413: File too large.
        HTTPException 415: Unsupported file type.
    """
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

    ext = get_extension(filename)
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"File type '.{ext}' is not supported. "
                f"Accepted types: {sorted(SUPPORTED_EXTENSIONS)}."
            ),
        )

    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    if len(content) > MAX_UPLOAD_SIZE_BYTES:
        limit_mb = MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds the {limit_mb} MB limit.",
        )

    return ext
