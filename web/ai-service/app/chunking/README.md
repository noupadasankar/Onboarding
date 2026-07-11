# chunking

## Purpose

This package is responsible for splitting raw document text — produced by `loaders/` — into smaller, overlapping segments suitable for embedding and vector storage. The chunking strategy affects retrieval quality directly: chunks that are too large dilute semantic signal; chunks that are too small lose necessary context.

Two strategies are provided: a fast recursive character-based splitter for general use, and a sentence-boundary-aware semantic splitter for documents where paragraph structure carries meaning.

## Responsibilities

- Accepting extracted text and metadata from the loader output
- Splitting text into chunks of a configurable size with configurable overlap
- Preserving source metadata (filename, page number, row index) on every chunk
- Returning a list of structured `Chunk` records ready for the embedding stage

## Does NOT Contain

- File reading or format parsing (that belongs in `loaders/`)
- Embedding computation (that belongs in `embeddings/`)
- Vector store writes (that belongs in `vectorstore/`)
- HTTP endpoint definitions (those live in `api/`)
- Database access of any kind

## Architecture Position

```
loaders/
    │
    │  List[DocumentRecord] { text, metadata }
    ▼
chunking/   ◄── splits text into overlapping segments
    │
    │  List[Chunk] { text, metadata, chunk_index }
    ▼
embeddings/
```

## Expected Contents

| File | Description | Status |
|---|---|---|
| `__init__.py` | Marks `chunking` as a Python package; exports a unified `chunk_document` entry point | Planned for Increment 4 |
| `recursive.py` | Fixed-size chunker with configurable `chunk_size` and `chunk_overlap`; splits on character boundaries, falling back through paragraph → sentence → word boundaries | Planned for Increment 4 |
| `semantic.py` | Sentence-boundary-aware chunker; groups sentences until a size threshold is reached, preserving semantic units | Planned for Increment 4 |

## Design Principles

- **Single Responsibility** — Each chunker file implements exactly one splitting strategy; strategy selection happens in `__init__.py`.
- **No Business Logic** — Chunkers split text; they make no decisions about relevance, storage, or retrieval.
- **No Database Access** — Chunking is a pure in-memory transformation.
- **Pure Functions** — Chunker functions take text and return chunks; they hold no mutable state between calls.
- **Stateless** — Chunking parameters (size, overlap) are passed at call time; no module-level configuration state.

## Current Status

Reserved for future implementation — the directory exists as a placeholder. No functional code has been written.

## Future Work

Increment 4 implements both chunking strategies. The recursive splitter covers the general case; the semantic splitter is added for document types where paragraph structure is significant (e.g., HR policy documents).
