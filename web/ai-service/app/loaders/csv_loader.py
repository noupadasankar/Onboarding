"""CSV document loader.

Parses delimiter-separated files using Python's built-in csv module.
BOM (byte-order mark) is stripped automatically via 'utf-8-sig'.
Falls back to Latin-1 for non-UTF-8 files (sufficient for typical HR exports).

The full content is serialised as newline-separated rows so downstream
chunkers and embedders can treat it like any other text document.
"""
import csv
import io

from app.loaders.base import BaseLoader
from app.loaders.exceptions import CorruptedFileError, EmptyFileError
from app.models.document import Document, FileType
from app.utils.metadata import clean_metadata


class CsvLoader(BaseLoader):
    @property
    def file_type(self) -> str:
        return "csv"

    def load(self, content: bytes, filename: str) -> Document:
        if not content:
            raise EmptyFileError(f"CSV file '{filename}' is empty.")

        text = self._decode(content, filename)

        try:
            dialect = csv.Sniffer().sniff(text[:4096], delimiters=",\t;|")
        except csv.Error:
            dialect = csv.excel  # type: ignore[assignment]

        try:
            reader = csv.reader(io.StringIO(text), dialect)
            rows = list(reader)
        except csv.Error as exc:
            raise CorruptedFileError(
                f"Cannot parse CSV '{filename}': {exc}"
            ) from exc

        if not rows:
            raise EmptyFileError(f"CSV file '{filename}' contains no rows.")

        headers = rows[0]
        data_rows = rows[1:]

        content_str = "\n".join(
            ", ".join(f"{col}: {val}" for col, val in zip(headers, row))
            for row in data_rows
        )

        metadata = clean_metadata(
            {
                "column_names": headers,
                "column_count": len(headers),
                "row_count": len(data_rows),
                "total_rows_including_header": len(rows),
                "delimiter": getattr(dialect, "delimiter", ","),
            }
        )

        return Document(
            filename=filename,
            file_type=FileType.CSV,
            mime_type="text/csv",
            content=content_str,
            metadata=metadata,
            page_count=None,
            source=filename,
            size_bytes=len(content),
        )

    @staticmethod
    def _decode(content: bytes, filename: str) -> str:
        try:
            return content.decode("utf-8-sig")
        except UnicodeDecodeError:
            return content.decode("latin-1", errors="replace")
