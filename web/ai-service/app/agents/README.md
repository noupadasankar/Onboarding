# agents

## Purpose
This package will house the LangGraph-based multi-agent system that powers OptiAgent's enterprise AI capabilities. A supervisor agent receives a user query, determines which domain it belongs to, and routes it to the appropriate specialist agent. Each specialist agent has access to a domain-scoped subset of the vector store and is equipped with tools tailored to its functional area.

The agent layer sits at the top of the AI processing stack: it consumes the RAG pipeline from `rag/`, the vector store from `vectorstore/`, and the LLM client, and it produces the final answer that is returned to the user via the `api/` layer.

## Responsibilities
- Defining the LangGraph state graph and execution workflow
- Implementing the supervisor agent that classifies queries and routes to domain specialists
- Implementing domain specialist agents for HR, Finance, and IT
- Managing inter-agent message passing and state transitions within a single graph execution
- Deciding when to invoke the RAG pipeline versus when to respond directly
- Returning a structured final answer to the calling router

## Does NOT Contain
- HTTP route definitions (those live in `api/`)
- Vector store client code (that lives in `vectorstore/`)
- Document loading logic (that lives in `loaders/`)
- Embedding computation (that lives in `rag/` or a dedicated embeddings module)
- Persistent state across requests — each graph execution is self-contained

## Architecture Position

```
api/v1/query.py
       │
       │  user query + session context
       ▼
agents/supervisor.py  ◄── classifies domain (HR / Finance / IT)
       │
       ├──► agents/hr_agent.py       ◄── HR policy, onboarding, benefits
       ├──► agents/finance_agent.py  ◄── Financial reports, budgets, expenses
       └──► agents/it_agent.py       ◄── IT support, systems, access requests
                │
                │  retrieval requests
                ▼
             rag/pipeline.py
```

## Expected Contents

| File | Description | Status |
|---|---|---|
| `__init__.py` | Marks `agents` as a Python package | Reserved |
| `supervisor.py` | Supervisor agent node; classifies incoming queries and emits routing decisions | Planned for Increment 10 |
| `hr_agent.py` | HR domain specialist; answers questions about policies, onboarding, and benefits | Planned for Increment 10 |
| `finance_agent.py` | Finance domain specialist; answers questions about budgets, expenses, and reports | Planned for Increment 10 |
| `it_agent.py` | IT domain specialist; answers questions about systems, access, and support procedures | Planned for Increment 10 |

## Design Principles
- **Single Responsibility** — Each agent file owns exactly one domain; routing logic stays in the supervisor.
- **Separation of Concerns** — Agents orchestrate; they do not implement retrieval, embedding, or HTTP handling directly.
- **Stateless** — Individual graph executions are stateless with respect to the process; conversation history is passed in via the request payload, not stored in module-level state.

## Current Status
Reserved for future implementation — the directory exists as a placeholder. No functional code has been written.

## Future Work
Increment 10 implements the full multi-agent system: supervisor routing logic and all three domain specialist agents (HR, Finance, IT). The LangGraph graph definition and shared state schema live in `graph/` (Increment 9), which must be implemented first.
