# providers

## Purpose

This package contains thin wrappers over external LLM provider APIs (Anthropic, OpenAI, Ollama). It isolates the rest of the application from provider-specific SDK details, authentication, and request formats. Swapping or adding a provider requires changes only within this package.

The provider abstraction is consumed by both the embedding layer (`embeddings/`) for vector generation and the RAG/agent layers for generation calls. A common interface means neither consumer needs to know which underlying model is active.

## Responsibilities

- Initialising provider clients with credentials from `core/config.py`
- Exposing a uniform interface for text generation (chat completion style)
- Exposing a uniform interface for embedding generation
- Handling provider-specific retry, rate-limit, and error responses
- Selecting the active provider based on application configuration

## Does NOT Contain

- Prompt construction or template management (that belongs in `prompts/`)
- RAG pipeline orchestration (that belongs in `rag/`)
- Agent logic or graph construction (those belong in `agents/` and `graph/`)
- HTTP endpoint definitions (those live in `api/`)
- Any domain-specific business logic

## Architecture Position

```
embeddings/service.py  ──► providers/  ──► Embedding API
rag/pipeline.py        ──► providers/  ──► LLM generation API
agents/*/              ──► providers/  ──► LLM generation API
```

## Expected Contents

| File | Description | Status |
|---|---|---|
| `__init__.py` | Marks `providers` as a Python package; exports a factory that returns the configured provider | Planned for Increment 8 |
| `anthropic.py` | Wrapper over the Anthropic SDK (Claude); implements the shared generation and embedding interfaces | Planned for Increment 8 |
| `openai.py` | Wrapper over the OpenAI SDK; implements the shared generation and embedding interfaces | Planned for Increment 8 |
| `ollama.py` | Wrapper over the Ollama HTTP API; provides a local, offline-capable alternative for development | Planned for Increment 8 |

## Design Principles

- **Single Responsibility** — Each provider file wraps exactly one external API.
- **Separation of Concerns** — Provider wrappers handle API mechanics only; they do not construct prompts or interpret results semantically.
- **Stateless** — Provider clients are created once (via dependency injection or module-level initialisation) and called statelessly per request.
- **No Business Logic** — Routing decisions, prompt assembly, and result interpretation happen in the layers above.

## Current Status

Reserved for future implementation — the directory exists as a placeholder. No functional code has been written.

## Future Work

Increment 8 implements all three provider wrappers and defines the shared generation interface. Anthropic (Claude) is the primary provider for OptiAgent; OpenAI and Ollama are added to support deployment flexibility and local development without external API access.
