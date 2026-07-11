"""Chunking package.

Exports the four pipeline components used by ChunkService:

  TextCleaner      — removes noise from raw document text
  SectionDetector  — identifies logical section boundaries
  TokenChunker     — splits into overlapping token windows
  ChunkValidator   — filters short, empty, and duplicate chunks
"""
from app.chunking.cleaner import TextCleaner, text_cleaner
from app.chunking.metadata_builder import MetadataBuilder
from app.chunking.section_detector import SectionDetector, section_detector
from app.chunking.token_chunker import TokenChunker, count_tokens
from app.chunking.validator import ChunkValidator, chunk_validator

__all__ = [
    "TextCleaner",
    "text_cleaner",
    "SectionDetector",
    "section_detector",
    "TokenChunker",
    "count_tokens",
    "ChunkValidator",
    "chunk_validator",
    "MetadataBuilder",
]
