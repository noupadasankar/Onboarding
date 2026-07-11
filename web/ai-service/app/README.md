# app

## Purpose

This is the root Python application package for the OptiAgent AI Service. It serves as the top-level namespace for all application code, grouping the FastAPI application entry point alongside the sub-packages that implement each architectural layer.

The `app` package establishes a clean boundary between application code and infrastructure-level concerns (tests, configuration files). Everything that runs at request time lives here; everything that supports development or deployment lives outside it.

## Responsibilities

- Exporting the FastAPI application instance via `main.py`
- Grouping all sub-packages under a single importable namespace
- Defining the top-level package boundary (`__init__.py`)

## Does NOT Contain

- Test files or fixtures (those live in `tests/`)
- Environment configuration files (`.env`, `pyproject.toml`, `Dockerfile`)
- Static assets or templates
- Any code that is not executed as part of the running service

## Architecture Position

```
HTTP Request
     │
     ▼
 main.py  ◄─── FastAPI app factory, middleware, lifespan hooks
     │
     ├── api/          ◄─── Routers and endpoint handlers
     ├── core/         ◄─── Config, logging, security
     ├── loaders/      ◄─── Document ingestion (Increment 3)
     ├── chunking/     ◄─── Text splitting (Increment 4)
     ├── embeddings/   ◄─── Vector generation (Increment 5)
     ├── vectorstore/  ◄─── ChromaDB integration (Increment 6)
     ├── rag/          ◄─── Retrieval-Augmented Generation pipeline (Increment 7)
     ├── providers/    ◄─── LLM provider wrappers (Increment 8)
     ├── graph/        ◄─── LangGraph StateGraph definition (Increment 9)
     ├── agents/       ◄─── Supervisor and domain agents (Increment 10)
     ├── prompts/      ◄─── Prompt templates (alongside Increment 7)
     └── memory/       ◄─── Conversation memory (alongside Increment 10)
```

## Expected Contents

| File / Folder | Description | Status |
|---|---|---|
| `__init__.py` | Marks `app` as a Python package | Implemented |
| `main.py` | FastAPI application factory; registers routers, middleware, and lifespan events | Implemented |
| `api/` | FastAPI routers and versioned endpoint definitions | Implemented |
| `core/` | Cross-cutting concerns: config, logging, security | Implemented |
| `loaders/` | Document loaders for PDF, CSV, DOCX, TXT, XLSX | Planned for Increment 3 |
| `chunking/` | Text splitting strategies (recursive, semantic) | Planned for Increment 4 |
| `embeddings/` | Embedding generation via configured provider | Planned for Increment 5 |
| `vectorstore/` | ChromaDB collection management and semantic search | Planned for Increment 6 |
| `rag/` | RAG pipeline: retriever, reranker, prompt builder | Planned for Increment 7 |
| `prompts/` | Prompt templates for RAG and agents | Planned alongside Increment 7 |
| `providers/` | LLM provider wrappers (Anthropic, OpenAI, Ollama) | Planned for Increment 8 |
| `graph/` | LangGraph StateGraph definition and compiled workflow | Planned for Increment 9 |
| `agents/` | Supervisor and domain agents (HR, Finance, IT) | Planned for Increment 10 |
| `memory/` | Conversation memory management | Planned alongside Increment 10 |

## Design Principles

- **Separation of Concerns** — Each sub-package owns exactly one capability layer; `main.py` wires them together without containing business logic.
- **Single Responsibility** — The `app` package is responsible only for defining the runnable service boundary; it delegates all functional concerns to sub-packages.
- **Organised by Capability** — Sub-packages are named after what they do (`chunking/`, `embeddings/`, `vectorstore/`), not after an abstract layer name (`services/`), to prevent them becoming dumping grounds.

## Current Status

Partially Implemented — `main.py`, `core/`, and `api/` are complete. All remaining sub-packages exist as reserved directories and will be populated incrementally.

## Future Work

- Increment 3: `loaders/`
- Increment 4: `chunking/`
- Increment 5: `embeddings/`
- Increment 6: `vectorstore/`
- Increment 7: `rag/` + `prompts/`
- Increment 8: `providers/`
- Increment 9: `graph/`
- Increment 10: `agents/` + `memory/`
