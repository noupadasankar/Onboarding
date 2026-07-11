# loaders

## Purpose
This package is responsible for document ingestion: reading raw files from disk or an upload stream, extracting their plain-text content, and returning structured records that include both the extracted text and any available metadata (filename, file type, page number, row index, etc.).

Loaders are the entry point for all document data in the system. Their output feeds directly into the chunking and embedding stages that follow in the ingestion pipeline. Keeping loaders in a dedicated package ensures they remain independently testable and replaceable without affecting downstream stages.

## Responsibilities
- Accepting a file path or byte stream as input
- Extracting plain-text content from the supported file formats (PDF, CSV, DOCX, TXT)
- Returning a list of structured document records, each containing extracted text and metadata
- Raising clear, typed exceptions when a file is malformed, unsupported, or unreadable

## Does NOT Contain
- Chunking or splitting logic (that is handled in a dedicated chunking module, Increment 4)
- Embedding computation (Increment 5)
- Vector store writes (Increment 6)
- HTTP endpoint definitions (those live in `api/`)
- Database access of any kind

## Architecture Position

```
api/v1/documents.py  (file upload endpoint)
          │
          │  file bytes + metadata
          ▼
    loaders/  ◄── format-specific extraction
          │
          │  List[DocumentRecord]
          │  { text: str, metadata: dict }
          ▼
    chunking (Increment 4)
          │
          ▼
    embeddings (Increment 5)
          │
          ▼
    vectorstore/
```

## Expected Contents

| File | Description | Status |
|---|---|---|
| `__init__.py` | Marks `loaders` as a Python package; exports a unified `load_document` dispatch function | Planned for Increment 3 |
| `base.py` | Abstract base class or `Protocol` defining the interface all loaders must satisfy | Planned for Increment 3 |
| `pdf_loader.py` | Extracts text page-by-page from PDF files; preserves page number as metadata | Planned for Increment 3 |
| `csv_loader.py` | Reads CSV rows; represents each row or a configurable row window as a document record | Planned for Increment 3 |
| `docx_loader.py` | Extracts paragraph text from DOCX files using `python-docx` | Planned for Increment 3 |
| `txt_loader.py` | Reads plain-text files; returns the full content as a single document record | Planned for Increment 3 |

## Design Principles
- **Single Responsibility** — Each loader file handles exactly one file format; format detection and dispatch live in `__init__.py`.
- **No Business Logic** — Loaders extract and normalize raw text; they make no decisions about relevance, chunking strategy, or storage.
- **No Database Access** — Loaders are pure input adapters; they do not write to any database.
- **Pure Functions** — Loader functions take a file input and return structured data; they do not maintain state between calls.

## Current Status
Reserved for future implementation — the directory exists as a placeholder. No functional code has been written.

## Future Work
Increment 3 implements all four loaders (`pdf_loader.py`, `csv_loader.py`, `docx_loader.py`, `txt_loader.py`) alongside the `base.py` interface and the dispatch entry point in `__init__.py`. A corresponding database migration (documents table) will also land in Increment 3.
