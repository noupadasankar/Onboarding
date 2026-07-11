# OptiAgent Demo Guide — Capstone Presentation

## Pre-Demo Checklist
- [ ] Docker services running (postgres, redis, chromadb)
- [ ] Node backend running (http://localhost:8000)
- [ ] AI service running (http://localhost:8100)
- [ ] Frontend running (http://localhost:5173 or nginx on :80)
- [ ] Database seeded (pnpm prisma:seed)
- [ ] Sample documents uploaded (see Scenario 2)
- [ ] All 4 demo accounts tested

## Demo Scenario 1 — Authentication & RBAC (3 minutes)
1. Open http://localhost/login
2. Log in as employee@optiagent.dev (Password123!)
3. Show: Dashboard loads, sidebar shows Chat and Documents only (no Users, Analytics)
4. Attempt to navigate to /users → show 403 Forbidden
5. Log out → log in as hr.manager@optiagent.dev
6. Show: sidebar now shows Users, Analytics, Admin Settings
7. Talking points: JWT RS256, role-based UI gating, permission checks at API layer

## Demo Scenario 2 — Document Management (3 minutes)
1. Log in as hr.manager@optiagent.dev
2. Navigate to Documents
3. Upload employee_handbook.txt (demo/documents/hr/)
4. Show: status changes PENDING → INDEXING → INDEXED (refresh page)
5. Upload benefits_guide.txt and performance_review_policy.txt
6. Switch to Finance: upload expense_policy.txt (demo/documents/finance/)
7. Switch to IT: upload it_security_policy.txt (demo/documents/it/)
8. Talking points: async fire-and-forget indexing, ChromaDB vector storage, multi-department docs

## Demo Scenario 3 — AI Chat (5 minutes)
This is the main demo. Use it.admin@optiagent.dev or hr.manager@optiagent.dev.

Question sequence (HR domain):
- "How many annual leave days do employees get each year?"
  Expected: 25 days, mention carry-forward limit
- "What is the company's parental leave policy?"
  Expected: 16 weeks primary, 4 weeks secondary
- "What happens during a probation period?"
  Expected: 3 months, reviewed, extended by written notice

Switch department to Finance:
- "What is the hotel allowance for London travel?"
  Expected: up to £150/night
- "When must expense claims be submitted by?"
  Expected: within 30 days

Follow-up (test conversation history):
- After the hotel question, ask: "What about international travel?"
  Expected: AI uses conversation context, answers £180/night
  Talking point: LangGraph conversation memory

IT questions:
- "What are the password requirements?"
  Expected: 12 chars, MFA mandatory, 90-day expiry
- "Can I use personal devices to access company systems?"
  Expected: company laptops only for production; BYOD phones via Intune

8. Talking points: multi-agent routing (Supervisor → domain agent), citation display, token usage tracking

## Demo Scenario 4 — Admin Features (2 minutes)
1. Log in as it.admin@optiagent.dev
2. Navigate to Users → show pagination, search, role badges
3. Navigate to Analytics → show questions per day, token usage
4. Navigate to Audit Logs → show trail of previous actions
5. Navigate to Admin Settings → demonstrate key/value config store
6. Talking points: observability, governance, production-ready admin

## Common Questions & Answers
Q: How does the AI know which agent to use?
A: The LangGraph Supervisor reads the user's department hint and question content. It routes to the HR, Finance, or IT agent based on LLM classification. Each agent has retrieval tools scoped to its department's ChromaDB collection.

Q: What if the document doesn't contain the answer?
A: Each agent is prompted to say "I couldn't find this in the provided documents" rather than hallucinate. Demo this with a made-up policy.

Q: How is security handled?
A: The browser never talks to the AI service. Node backend authenticates via RS256 JWT, checks RBAC permissions, then forwards user context to the AI service via a shared internal service token. The AI service verifies this token with hmac.compare_digest.

Q: Can it handle multiple file types?
A: Yes — PDF, DOCX, TXT, CSV, XLSX. The document service uses the appropriate extractor per MIME type.

Q: Is conversation history maintained?
A: Yes. Each conversation has an ID on both the Node (Postgres) and AI (ChromaDB) sides. The AI service retrieves the last N messages to maintain context.
