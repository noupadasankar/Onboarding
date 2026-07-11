"""Upload constraints re-exported for OpenAPI documentation.

Imports the source-of-truth values from file_utils so the docs and
validation code stay in sync automatically.
"""
from app.utils.file_utils import (
    EXTENSION_MIME_MAP,
    MAX_UPLOAD_SIZE_BYTES,
    SUPPORTED_EXTENSIONS,
)

MAX_UPLOAD_SIZE_MB: int = MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)

__all__ = [
    "SUPPORTED_EXTENSIONS",
    "EXTENSION_MIME_MAP",
    "MAX_UPLOAD_SIZE_BYTES",
    "MAX_UPLOAD_SIZE_MB",
]
