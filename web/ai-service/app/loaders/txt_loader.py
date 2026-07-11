"""Plain-text document loader.

Attempts UTF-8 decoding first; falls back to chardet auto-detection for
legacy encodings (Latin-1, Windows-1252, etc.). Raises InvalidEncodingError
if chardet cannot identify the encoding with acceptable confidence.
"""
import chardet

from app.loaders.base import BaseLoader
from app.loaders.exceptions import EmptyFileError, InvalidEncodingError
from app.models.document import Document, FileType
from app.utils.metadata import clean_metadata

_MIN_CHARDET_CONFIDENCE = 0.7


class TxtLoader(BaseLoader):
    @property
    def file_type(self) -> str:
        return "txt"

    def load(self, content: bytes, filename: str) -> Document:
        if not content:
            raise EmptyFileError(f"Text file '{filename}' is empty.")

        encoding, text = self._decode(content, filename)

        lines = text.splitlines()
        non_empty_lines = [ln for ln in lines if ln.strip()]

        metadata = clean_metadata(
            {
                "encoding": encoding,
                "line_count": len(lines),
                "non_empty_line_count": len(non_empty_lines),
                "word_count": len(text.split()),
                "char_count": len(text),
            }
        )

        return Document(
            filename=filename,
            file_type=FileType.TXT,
            mime_type="text/plain",
            content=text,
            metadata=metadata,
            page_count=None,
            source=filename,
            size_bytes=len(content),
        )

    @staticmethod
    def _decode(content: bytes, filename: str) -> tuple[str, str]:
        # Try UTF-8 (with BOM stripping) first — the common case.
        try:
            return "utf-8", content.decode("utf-8-sig")
        except UnicodeDecodeError:
            pass

        # Auto-detect encoding via chardet.
        result = chardet.detect(content)
        encoding = result.get("encoding")
        confidence = result.get("confidence", 0.0) or 0.0

        if not encoding or confidence < _MIN_CHARDET_CONFIDENCE:
            raise InvalidEncodingError(
                f"Cannot determine encoding of '{filename}' "
                f"(chardet confidence {confidence:.0%})."
            )

        try:
            return encoding, content.decode(encoding)
        except (UnicodeDecodeError, LookupError) as exc:
            raise InvalidEncodingError(
                f"Cannot decode '{filename}' with detected encoding '{encoding}': {exc}"
            ) from exc
