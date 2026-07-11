# prompts

## Purpose

This package manages prompt templates used by the RAG pipeline and agent layer when constructing requests to the LLM. Keeping templates here — rather than inline in agent or pipeline code — makes them easy to review, version, and adjust without touching logic files.

Templates are structured strings with named placeholders. They are rendered at runtime with retrieved context, user query, and conversation history, then passed to the LLM via `providers/`.

## Responsibilities

- Defining and storing prompt templates as structured Python objects (not raw strings scattered through the codebase)
- Rendering templates by substituting named placeholders with runtime values
- Providing domain-specific templates for each agent (HR, Finance, IT) and for the RAG pipeline
- Versioning templates so changes can be tracked and rolled back if answer quality degrades

## Does NOT Contain

- LLM API calls (those go through `providers/`)
- Retrieval logic (that belongs in `rag/`)
- Agent routing decisions (that belong in `agents/` and `graph/`)
- HTTP endpoint definitions (those live in `api/`)
- Persistent storage — templates are defined in code and optionally cached; database-backed templates would require a dedicated migration and belong in a `db/` layer added at that time

## Architecture Position

```
rag/prompt_builder.py  ──► prompts/  ──► rendered prompt string
agents/hr_agent.py     ──► prompts/  ──► domain-specific system prompt
agents/*/              ──► prompts/  ──► rendered prompt string
                               │
                               ▼
                          providers/  (LLM call)
```

## Expected Contents

| File | Description | Status |
|---|---|---|
| `__init__.py` | Marks `prompts` as a Python package | Not yet assigned to an increment |
| `base.py` | Base `PromptTemplate` class or `Protocol` with a `render(**kwargs) -> str` interface | Not yet assigned to an increment |
| `rag_prompts.py` | Templates for the RAG pipeline: system context, retrieved-chunks insertion, answer format instructions | Not yet assigned to an increment |
| `agent_prompts.py` | Domain-specific system prompts for HR, Finance, and IT agents | Not yet assigned to an increment |

## Design Principles

- **Single Responsibility** — This package owns template definitions and rendering only; it has no knowledge of retrieval, generation, or routing.
- **No Business Logic** — Templates are rendering functions; they do not decide which template to use or evaluate the quality of the output.
- **Pure Functions** — Template rendering is a deterministic string substitution given the same inputs; no side effects.
- **Separation of Concerns** — Prompt content is separated from the code that calls the LLM, making it straightforward to update wording without touching pipeline logic.

## Current Status

Reserved for future implementation — the directory exists as a placeholder. No functional code has been written.

## Future Work

Increment not yet assigned. Prompts become necessary when the RAG pipeline (Increment 7) is implemented; initial templates will be introduced alongside `rag/prompt_builder.py` at that point.
