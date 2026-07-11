"""Abstract base class for all document loaders.

Loaders are stateless. All file-format-specific logic lives in the subclass;
the rest of the pipeline only ever calls `loader.load(content, filename)`.
"""
from abc import ABC, abstractmethod

from app.models.document import Document


class BaseLoader(ABC):
    """Contract every loader must fulfil.

    Implementors receive raw bytes and a filename and must return a fully
    populated Document. They may raise any subclass of LoaderError to signal
    a problem with the file itself (not a programming error).
    """

    @abstractmethod
    def load(self, content: bytes, filename: str) -> Document:
        """Parse `content` and return a unified Document.

        Args:
            content: Raw file bytes as received from the upload.
            filename: Original filename (used for metadata and error messages).

        Returns:
            A fully populated Document instance.

        Raises:
            EmptyFileError: The file has no bytes or no extractable content.
            CorruptedFileError: The file cannot be parsed.
            PasswordProtectedFileError: The file is encrypted.
            InvalidEncodingError: The text encoding cannot be determined.
        """

    @property
    @abstractmethod
    def file_type(self) -> str:
        """The file extension this loader handles (lower-case, without dot)."""
