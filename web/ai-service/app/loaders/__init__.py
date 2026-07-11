"""Document loader package.

Each loader converts raw file bytes to the unified Document model.
The LoaderFactory maps file extensions to the correct loader instance.

Usage:
    from app.loaders.factory import LoaderFactory
    loader = LoaderFactory.get_loader("pdf")
    document = loader.load(content_bytes, "report.pdf")
"""
from app.loaders.factory import LoaderFactory

__all__ = ["LoaderFactory"]
