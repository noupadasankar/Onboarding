"""Loader factory — maps file extensions to loader instances.

All loaders are singletons (created once at import time); they are stateless
so this is safe. Call `LoaderFactory.get_loader(ext)` with the lowercase
extension (no dot) to get the appropriate loader.
"""
from app.loaders.base import BaseLoader
from app.loaders.csv_loader import CsvLoader
from app.loaders.docx_loader import DocxLoader
from app.loaders.exceptions import UnsupportedFileTypeError
from app.loaders.pdf_loader import PdfLoader
from app.loaders.txt_loader import TxtLoader
from app.loaders.xlsx_loader import XlsxLoader

_REGISTRY: dict[str, BaseLoader] = {
    loader.file_type: loader
    for loader in [
        PdfLoader(),
        DocxLoader(),
        TxtLoader(),
        CsvLoader(),
        XlsxLoader(),
    ]
}


class LoaderFactory:
    @staticmethod
    def get_loader(extension: str) -> BaseLoader:
        """Return the loader for `extension` (lower-case, without dot).

        Raises:
            UnsupportedFileTypeError: No loader is registered for this extension.
        """
        loader = _REGISTRY.get(extension.lower())
        if loader is None:
            supported = sorted(_REGISTRY)
            raise UnsupportedFileTypeError(
                f"No loader for '.{extension}'. Supported: {supported}."
            )
        return loader

    @staticmethod
    def supported_extensions() -> list[str]:
        return sorted(_REGISTRY)
