"""PDF document loader.

Uses pypdf (>=4.3) to extract text and document metadata from PDF files.
Handles encrypted PDFs by attempting a blank-password decrypt; raises
PasswordProtectedFileError if decryption fails.
"""
import io
from typing import Any

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.loaders.base import BaseLoader
from app.loaders.exceptions import CorruptedFileError, EmptyFileError, PasswordProtectedFileError
from app.models.document import Document, FileType
from app.utils.metadata import clean_metadata


class PdfLoader(BaseLoader):
    @property
    def file_type(self) -> str:
        return "pdf"

    def load(self, content: bytes, filename: str) -> Document:
        if not content:
            raise EmptyFileError(f"PDF file '{filename}' is empty.")

        try:
            reader = PdfReader(io.BytesIO(content))
        except PdfReadError as exc:
            raise CorruptedFileError(f"Cannot read PDF '{filename}': {exc}") from exc
        except Exception as exc:
            raise CorruptedFileError(
                f"Unexpected error reading PDF '{filename}': {exc}"
            ) from exc

        if reader.is_encrypted:
            try:
                decrypted = reader.decrypt("")
                # pypdf returns 0 (falsy) when decryption fails
                if not decrypted:
                    raise PasswordProtectedFileError(
                        f"PDF '{filename}' is password-protected."
                    )
            except PasswordProtectedFileError:
                raise
            except Exception as exc:
                raise PasswordProtectedFileError(
                    f"PDF '{filename}' is password-protected."
                ) from exc

        pages = reader.pages
        page_count = len(pages)

        text_parts: list[str] = []
        for page in pages:
            text = page.extract_text()
            if text and text.strip():
                text_parts.append(text.strip())

        content_str = "\n\n".join(text_parts)

        raw_meta: dict[str, Any] = {"page_count": page_count}
        info = reader.metadata
        if info:
            raw_meta["title"] = info.title
            raw_meta["author"] = info.author
            raw_meta["subject"] = info.subject
            raw_meta["creator"] = info.creator
            raw_meta["producer"] = info.producer

        return Document(
            filename=filename,
            file_type=FileType.PDF,
            mime_type="application/pdf",
            content=content_str,
            metadata=clean_metadata(raw_meta),
            page_count=page_count,
            source=filename,
            size_bytes=len(content),
        )
