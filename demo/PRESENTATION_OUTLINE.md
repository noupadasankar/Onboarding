# OptiAgent — Capstone Presentation Outline

## Slide 1 — Title
OptiAgent: Enterprise AI Platform for Knowledge Work
Deloitte Technology Consulting Capstone 2026
[Team Member Name] | [Date]

## Slide 2 — Problem Statement
- Enterprise knowledge is siloed across HR, Finance, IT departments
- Employees waste ~20% of work time searching for policy information
- Inconsistent policy interpretation creates compliance risk
- Existing solutions (SharePoint search) lack natural language understanding

## Slide 3 — Solution
OptiAgent: A secure, multi-agent AI platform that:
- Understands natural language questions about company policies
- Routes to the right domain expert (HR, Finance, IT)
- Only answers from approved, uploaded company documents
- Enforces role-based access — finance queries require finance permissions
- Maintains full audit trail of every AI interaction

## Slide 4 — Architecture Overview
[Insert architecture diagram from README]
Three-service architecture:
- React Frontend → Node.js Gateway (auth, RBAC) → Python AI Service (LangGraph, RAG)
- Trust boundary: browser never touches AI service
- Data stores: PostgreSQL (business data), ChromaDB (vectors), Redis (sessions)

## Slide 5 — Technology Stack
Frontend: React 19 · Redux Toolkit · RTK Query · Tailwind CSS
Backend: Node.js · Express · TypeScript · InversifyJS · Prisma
AI Service: Python · FastAPI · LangGraph · LangChain · OpenAI
Database: PostgreSQL 16 · ChromaDB · Redis 7
Infrastructure: Docker · Nginx · GitHub Actions CI/CD

## Slide 6 — Key Engineering Decisions (ADRs)
ADR-0001: Three-service split (frontend / gateway / AI)
  Why: Clean trust boundary, independent deployability, language-optimised services
ADR-0002: Node gateway rather than direct AI access
  Why: Single enforcement point for auth + RBAC; AI service stays stateless

## Slide 7 — AI Pipeline
[Insert RAG chat sequence diagram]
1. Question → LangGraph Supervisor
2. Supervisor routes to domain agent (HR / Finance / IT)
3. Agent embeds question, queries ChromaDB
4. Context chunks + conversation history → LLM prompt
5. GPT-4 generates answer + citations

## Slide 8 — Security Model
- JWT RS256 asymmetric keys (not HS256)
- Refresh token rotation (Redis-backed blacklist)
- Internal service token (HMAC verified) — never exposed to browser
- All AI calls carry X-User-Id + X-User-Role for audit trail
- Permissions checked at Node layer before any AI call

## Slide 9 — Live Demo
[Run Demo Scenarios 1-4]

## Slide 10 — What I Would Do Next
- End-to-end Playwright tests
- Streaming responses (SSE) to frontend
- Multi-tenant isolation in ChromaDB
- Cost dashboards (OpenAI spend per department)
- SOC 2 compliance controls
- Kubernetes deployment manifest

## Slide 11 — Lessons Learned
- Fire-and-forget async indexing avoids blocking uploads on ChromaDB
- Sharing the RBAC contract between frontend and backend eliminates drift
- LangGraph state management is powerful but debugging requires structured logging
- HMAC token guard on the AI service is simpler and more auditable than OAuth between services
