# HR Onboarding AI Employee 🤖

> **Deloitte Technology Consulting Capstone 2026**  
> *An autonomous, governance-aware HR Onboarding Conversational Assistant with multi-turn task tracking, grounded policy Q&A, and citation inspection.*

---

## 📌 Scenario & Evaluation Rubric

| Scenario | Build a conversational agent that walks a new hire through onboarding questions — benefits, IT setup, policies — using provided FAQ and policy documents, and can create and track simple onboarding tasks. |
| :--- | :--- |
| **Groundedness & Accuracy** | Answers strictly derived from uploaded policy & FAQ documents with source citations. |
| **Task-Tracking Correctness** | Creates, stores, retrieves, and completes onboarding tasks across multi-turn dialogue. |
| **Conversational Design** | Warm, professional, clean markdown formatting with interactive dual-pane UI. |

---

## 🌟 Key Features

1. **Dual-Pane Onboarding Hub**:
   - **Left Pane**: Conversational AI assistant with real-time streaming, suggested quick question chips, markdown rendering, and clickable source citation badges.
   - **Right Pane**: Interactive Onboarding Checklist with animated visual progress bar (`% Complete`), category filters (`HR`, `IT`, `Finance`, `Compliance`, `General`), one-click completion checkboxes, and task management modals.

2. **Grounded Multi-Document RAG**:
   - Auto-bootstrapped vector store indexing all 8 enterprise policy documents on startup (`Onboarding_Process.txt`, `HR_FAQs.csv`, `Leave_Policy.docx`, `Company_Policy.docx`, `IT_FAQs.csv`, `IT_Policy.docx`, `Expense_Guidelines.txt`, `Finance_FAQs.csv`).
   - Semantic chunking with local sentence embeddings (`all-MiniLM-L6-v2`) and ultra-fast LLM completion via Groq.

3. **Conversational Task Actions (Multi-Turn Memory)**:
   - *"Show my onboarding tasks"* → Lists active tasks grouped by status (Pending, In Progress, Completed).
   - *"Create a task for benefits enrollment by next Friday"* → Extracts title, category, priority, and due date from dialogue.
   - *"Mark 1Password & MFA as completed"* → Fuzzy title matching with instant status & progress update.

4. **Source Document Citation Inspector**:
   - Every answer cites the source document and section.
   - Clicking on any citation opens an excerpt modal showing the exact text chunk and match score.

---

## 🏗️ System Architecture

```
                               ┌───────────────────────────┐
                               │  React 19 Frontend (:3000)│
                               │   Dual-Pane Onboarding    │
                               └─────────────┬─────────────┘
                                             │ HTTP / REST
                                             ▼
                               ┌───────────────────────────┐
                               │  Node.js Gateway (:8000)  │
                               │  Inversify DI · Auth RBAC │
                               │  PostgreSQL · Redis Store │
                               └─────────────┬─────────────┘
                                             │ Internal Token Forwarding
                                             ▼
                               ┌───────────────────────────┐
                               │  FastAPI AI Service(:8100)│
                               │  LangGraph Supervisor     │
                               │  HR Onboarding Agent Node │
                               └─────────────┬─────────────┘
                                             │
                      ┌──────────────────────┴──────────────────────┐
                      ▼                                             ▼
          ┌────────────────────────┐                   ┌────────────────────────┐
          │ ChromaDB Vector Store  │                   │  Groq / LLaMA / OpenAI │
          │ 375 Indexed Chunks     │                   │  Low-Latency LLM       │
          └────────────────────────┘                   └────────────────────────┘
```

---

## 🚀 Quick Start Guide

### Prerequisites
- Node.js 20+ & `pnpm` 8+
- Python 3.11
- PostgreSQL (`localhost:5432`) & Redis (`localhost:6379`)

### 1. Install Dependencies
```bash
pnpm install
cd web/ai-service && pip install -e ".[dev]"
```

### 2. Configure Environment Variables
- `web/ai-service/.env`:
  ```env
  APP_ENV=development
  APP_PORT=8100
  INTERNAL_SERVICE_TOKEN=change-me-internal-service-token
  CHROMA_MODE=memory
  LLM_PROVIDER=openai
  LLM_MODEL=openai/gpt-oss-120b
  OPENAI_API_KEY=your_groq_api_key_here
  OPENAI_BASE_URL=https://api.groq.com/openai/v1
  ```
- `web/backend/.env`:
  ```env
  DATABASE_URL=postgresql://postgres:postgres@localhost:5432/optiagent?schema=public
  REDIS_URL=redis://localhost:6379/0
  AI_SERVICE_URL=http://localhost:8100
  INTERNAL_SERVICE_TOKEN=change-me-internal-service-token
  ```

### 3. Run the Services

You can start all three services simultaneously or in separate terminal tabs:

#### Tab 1 — AI Service (:8100)
```bash
cd web/ai-service
python -m uvicorn app.main:app --port 8100
```

#### Tab 2 — Backend API (:8000)
```bash
pnpm --filter @hr-onboarding/backend dev
```

#### Tab 3 — Frontend UI (:3000)
```bash
pnpm --filter @hr-onboarding/frontend dev
```

---

## 🔑 Demo Login Accounts

All accounts use the password: **`Password123!`**

| Email | Role | Access / Permissions |
| :--- | :--- | :--- |
| `employee@optiagent.dev` | **EMPLOYEE** (New Hire) | Onboarding Q&A, Personal Checklist, General Policies |
| `hr.manager@optiagent.dev` | **HR_MANAGER** | Full HR Knowledge Base & Employee Onboarding Overview |
| `it.admin@optiagent.dev` | **IT_ADMIN** | IT Provisioning, Device Policies, User Management |
| `finance.admin@optiagent.dev` | **FINANCE_ADMIN** | Payroll, Direct Deposit, Expense Guidelines |

---

## 🧪 Testing & Verification

Run automated test suites across the repository:

```bash
# Run all unit and integration tests (45 tests)
pnpm --filter @hr-onboarding/backend test

# Run global TypeScript typecheck (0 errors)
pnpm typecheck
```

---

## 📂 Project Structure

```
.
├── web/
│   ├── frontend/                # React 19 SPA with dual-pane Onboarding Hub
│   │   └── src/features/onboarding/
│   │       ├── api/             # RTK Query client (chat, tasks, overview)
│   │       ├── components/      # ChatMessage, TaskList, TaskFormModal
│   │       └── pages/           # OnboardingChatPage.tsx
│   ├── backend/                 # Node.js Express API & Inversify DI Gateway
│   │   └── src/modules/onboarding/
│   │       ├── application/     # Controller, Service, Routes
│   │       ├── domain/          # OnboardingTask entity & interfaces
│   │       └── infrastructure/  # In-memory repository with default seed tasks
│   └── ai-service/              # Python FastAPI LangGraph AI service
│       └── app/
│           ├── agents/          # Onboarding agent with RAG & TaskTool
│           ├── rag/             # Chunking, embeddings & vector retrieval
│           └── tools/           # TaskTool with fuzzy status matching
├── shared/                      # Pure TypeScript cross-service contracts
└── data/raw/                    # HR/IT/Finance policy documents and FAQs
```

---

## 📄 License
UNLICENSED — Deloitte Capstone 2026 Internal Submission.

