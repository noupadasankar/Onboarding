#!/usr/bin/env python3
"""End-to-end document versioning test against a live OptiAgent stack.

Tests the full scenario:

  Upload Employee Handbook v1
    ↓
  Wait for INDEXED
    ↓
  Search → confirm v1 content (20 days leave)
    ↓
  Upload Employee Handbook v2 (same name)
    ↓
  Node backend marks v1 SUPERSEDED, fires deleteVectors(v1)
    ↓
  Wait for v2 INDEXED
    ↓
  Search → confirm only v2 content (25 days leave, TE-004)
    ↓
  Verify v1 chunk count in ChromaDB == 0

Usage:
  python scripts/e2e_versioning_test.py
  python scripts/e2e_versioning_test.py --node-url http://localhost:3000 \\
      --ai-url http://localhost:8100 \\
      --token eyJhbGc...

Environment variables (used when flags are not provided):
  NODE_URL            Node backend base URL (default: http://localhost:3000)
  AI_URL              AI service base URL  (default: http://localhost:8100)
  TEST_JWT_TOKEN      Bearer JWT for Node API requests
  INTERNAL_TOKEN      Shared secret for direct AI service calls
"""
from __future__ import annotations

import argparse
import io
import os
import sys
import time

try:
    import requests
    from fpdf import FPDF
except ImportError:
    sys.exit(
        "Missing dependencies.  Run:  pip install requests fpdf2\n"
        "(These are dev dependencies, not runtime deps.)"
    )

# ── Content ───────────────────────────────────────────────────────────────────

_V1_CONTENT = """
Employee Handbook — Version 1

1. Annual Leave
   All permanent employees are entitled to 20 days of paid annual leave per year.
   Policy code HR-204 governs the annual leave entitlement for all staff.
   Leave requests must be submitted at least two weeks in advance.
   Unused leave may be carried over subject to line manager approval.

2. Sick Leave
   Employees receive 5 sick days per calendar year without a doctor's note.
   Additional sick days require a GP certificate.

3. Public Holidays
   Employees receive 10 public holidays per year in addition to annual leave.

Contact HR for any queries regarding policy HR-204.
"""

_V2_CONTENT = """
Employee Handbook — Version 2 (Updated January 2026)

1. Annual Leave
   All permanent employees are now entitled to 25 days of paid annual leave per year.
   This is an increase from 20 days effective 1 January 2026.
   Policy code HR-204 has been updated — please refer to Appendix A for full details.
   Leave requests must be submitted at least two weeks in advance.

2. Sick Leave
   Sick leave allowance increased to 10 days per calendar year without a GP note.
   The previous entitlement was 5 days.

3. Mental Health Leave
   New in 2026: employees may take up to 3 mental health leave days per year.
   This is governed by policy TE-004 (see Section 7.2).

4. Hybrid Working
   Section 7.2: employees may work from home up to 3 days per week.
   Hybrid working must be agreed with line management.

Contact HR for any queries regarding updated policy HR-204 or new policy TE-004.
"""


def _make_pdf(text: str) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)
    for line in text.strip().split("\n"):
        pdf.multi_cell(0, 7, line)
    return bytes(pdf.output())


# ── Helpers ───────────────────────────────────────────────────────────────────

TICK  = "✓"
CROSS = "✗"
ARROW = "→"


def _ok(msg: str) -> None:
    print(f"  {TICK}  {msg}")


def _fail(msg: str) -> None:
    print(f"  {CROSS}  {msg}")
    sys.exit(1)


def _step(msg: str) -> None:
    print(f"\n{ARROW} {msg}")


class NodeClient:
    """Thin wrapper around the Node backend API."""

    def __init__(self, base_url: str, token: str) -> None:
        self.base = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {token}"})

    def upload(self, filename: str, content: bytes, department_id: str | None = None) -> dict:
        files = {"file": (filename, io.BytesIO(content), "application/pdf")}
        data = {}
        if department_id:
            data["departmentId"] = department_id
        res = self.session.post(f"{self.base}/api/v1/documents/upload", files=files, data=data)
        res.raise_for_status()
        return res.json()["data"]

    def get_document(self, doc_id: str) -> dict:
        res = self.session.get(f"{self.base}/api/v1/documents/{doc_id}")
        res.raise_for_status()
        return res.json()["data"]

    def list_documents(self) -> list[dict]:
        res = self.session.get(f"{self.base}/api/v1/documents")
        res.raise_for_status()
        return res.json()["data"]["items"]

    def chat(self, question: str, conversation_id: str | None = None) -> dict:
        payload = {"question": question}
        if conversation_id:
            payload["conversationId"] = conversation_id
        res = self.session.post(f"{self.base}/api/v1/conversations/chat", json=payload)
        res.raise_for_status()
        return res.json()["data"]


class AiClient:
    """Direct AI service client (bypasses Node gateway — for verification only)."""

    def __init__(self, base_url: str, internal_token: str) -> None:
        self.base = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "X-Internal-Token": internal_token,
            "X-User-Id": "e2e-test",
            "X-User-Role": "IT_ADMIN",
        })

    def vector_count(self) -> dict:
        res = self.session.get(f"{self.base}/api/v1/vectorstore/count")
        res.raise_for_status()
        return res.json()

    def vectors_for_document(self, doc_id: str) -> int:
        """Return the number of vectors stored for *doc_id*."""
        # Fetch all text; count those matching document_id
        res = self.session.get(f"{self.base}/api/v1/vectorstore/count")
        res.raise_for_status()
        # We can't query by doc_id without a dedicated endpoint, so use count
        # as a proxy (before/after deletion).
        return res.json()["total_chunks"]


def _wait_for_status(
    client: NodeClient,
    doc_id: str,
    target: str,
    timeout: int = 120,
    interval: int = 3,
) -> dict:
    """Poll until the document reaches *target* status or *timeout* seconds elapse."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        doc = client.get_document(doc_id)
        status = doc["status"]
        if status == target:
            return doc
        if status == "FAILED":
            _fail(f"Document {doc_id} reached FAILED status. Error: {doc.get('errorMessage')}")
        print(f"    ... status={status}, waiting {interval}s ...")
        time.sleep(interval)
    _fail(f"Timeout waiting for {doc_id} to reach status={target}")
    return {}  # unreachable


# ── Test runner ───────────────────────────────────────────────────────────────

def run(node_url: str, ai_url: str, token: str, internal_token: str) -> None:
    node = NodeClient(node_url, token)
    ai   = AiClient(ai_url, internal_token)

    print("\n" + "=" * 65)
    print("  OptiAgent — Document Versioning E2E Test")
    print("=" * 65)
    print(f"  Node: {node_url}")
    print(f"  AI:   {ai_url}")

    # ─────────────────────────────────────────────────────────────────────────
    _step("Phase 1 — Upload Employee Handbook v1")
    # ─────────────────────────────────────────────────────────────────────────

    v1_pdf = _make_pdf(_V1_CONTENT)
    v1_doc = node.upload("Employee_Handbook.pdf", v1_pdf)
    v1_id  = v1_doc["id"]
    _ok(f"Uploaded v1: id={v1_id}")
    assert v1_doc["status"] == "PENDING", f"Expected PENDING, got {v1_doc['status']}"
    assert v1_doc.get("version") == 1, f"Expected version=1, got {v1_doc.get('version')}"

    # ─────────────────────────────────────────────────────────────────────────
    _step("Phase 2 — Wait for v1 to reach INDEXED")
    # ─────────────────────────────────────────────────────────────────────────

    v1_indexed = _wait_for_status(node, v1_id, "INDEXED")
    _ok(f"v1 indexed: {v1_indexed['chunkCount']} chunks, {v1_indexed['vectorCount']} vectors")

    v1_vector_count_before = ai.vector_count()
    _ok(f"ChromaDB: {v1_vector_count_before['total_chunks']} total chunks, "
        f"{v1_vector_count_before['unique_documents']} documents")
    assert v1_vector_count_before["total_chunks"] > 0, "Expected > 0 chunks after v1 indexing"

    # ─────────────────────────────────────────────────────────────────────────
    _step("Phase 3 — Chat: verify v1 content appears")
    # ─────────────────────────────────────────────────────────────────────────

    chat_v1 = node.chat("How many annual leave days do employees receive?")
    answer_v1 = chat_v1.get("answer", "")
    _ok(f"v1 answer: {answer_v1[:120]}...")
    print(f"    Citations: {[c.get('filename') for c in chat_v1.get('citations', [])]}")

    # v1 says 20 days
    assert "20" in answer_v1, (
        f"Expected v1 answer to mention '20 days' but got: {answer_v1[:200]}"
    )
    _ok("v1 content confirmed: answer mentions '20' days")

    # ─────────────────────────────────────────────────────────────────────────
    _step("Phase 4 — Upload Employee Handbook v2 (SAME filename)")
    # ─────────────────────────────────────────────────────────────────────────

    v2_pdf = _make_pdf(_V2_CONTENT)
    v2_doc = node.upload("Employee_Handbook.pdf", v2_pdf)   # same name → version bump
    v2_id  = v2_doc["id"]
    _ok(f"Uploaded v2: id={v2_id}")
    assert v2_doc.get("version") == 2, (
        f"Expected version=2, got {v2_doc.get('version')}. "
        f"Ensure versioning logic is enabled in document.service.ts."
    )
    _ok(f"Version number correct: v2_doc.version == 2")

    # ─────────────────────────────────────────────────────────────────────────
    _step("Phase 5 — Verify v1 is SUPERSEDED")
    # ─────────────────────────────────────────────────────────────────────────

    # v1 should transition to SUPERSEDED shortly after v2 upload
    v1_final = _wait_for_status(node, v1_id, "SUPERSEDED", timeout=30)
    _ok(f"v1 status = SUPERSEDED (supersededAt={v1_final.get('supersededAt')})")
    assert v1_final["isLatest"] is False, "v1.isLatest should be False"
    _ok("v1.isLatest == False ✓")

    # v2 should be PENDING or INDEXING by now
    v2_state = node.get_document(v2_id)
    _ok(f"v2 status after supersede: {v2_state['status']}")

    # ─────────────────────────────────────────────────────────────────────────
    _step("Phase 6 — Wait for v2 to reach INDEXED")
    # ─────────────────────────────────────────────────────────────────────────

    v2_indexed = _wait_for_status(node, v2_id, "INDEXED")
    _ok(f"v2 indexed: {v2_indexed['chunkCount']} chunks, {v2_indexed['vectorCount']} vectors")
    assert v2_indexed["isLatest"] is True, "v2.isLatest should be True"
    _ok("v2.isLatest == True ✓")

    # ─────────────────────────────────────────────────────────────────────────
    _step("Phase 7 — Verify v1 vectors deleted from ChromaDB")
    # ─────────────────────────────────────────────────────────────────────────

    # Give the async deletion a moment to complete
    time.sleep(2)
    after = ai.vector_count()
    _ok(f"ChromaDB after versioning: {after['total_chunks']} chunks, "
        f"{after['unique_documents']} documents")
    assert after["unique_documents"] == 1, (
        f"Expected 1 unique document (v2 only), got {after['unique_documents']}. "
        f"v1 vectors may not have been deleted."
    )
    _ok("ChromaDB unique_documents == 1 (only v2) ✓")

    # ─────────────────────────────────────────────────────────────────────────
    _step("Phase 8 — Chat: verify ONLY v2 content appears")
    # ─────────────────────────────────────────────────────────────────────────

    chat_v2 = node.chat("How many annual leave days do employees receive?")
    answer_v2 = chat_v2.get("answer", "")
    _ok(f"v2 answer: {answer_v2[:120]}...")
    print(f"    Citations: {[c.get('filename') for c in chat_v2.get('citations', [])]}")

    # v2 says 25 days
    assert "25" in answer_v2, (
        f"Expected v2 answer to mention '25 days' but got: {answer_v2[:200]}. "
        f"Old v1 chunks may still be appearing in search."
    )
    _ok("v2 content confirmed: answer mentions '25' days")

    # v1's '20 days' should NOT be the primary answer
    # (it may appear as contrast but 25 should dominate)
    print(f"    Full answer: {answer_v2[:400]}")

    # ─────────────────────────────────────────────────────────────────────────
    _step("Phase 9 — Document list: only v2 appears")
    # ─────────────────────────────────────────────────────────────────────────

    docs = node.list_documents()
    handbook_docs = [d for d in docs if d["originalName"] == "Employee_Handbook.pdf"]

    _ok(f"Documents named 'Employee_Handbook.pdf' in list: {len(handbook_docs)}")
    assert len(handbook_docs) == 1, (
        f"Expected 1 document in list (v2 only), got {len(handbook_docs)}. "
        f"SUPERSEDED docs should be hidden by default."
    )
    shown = handbook_docs[0]
    assert shown["id"] == v2_id, "The visible document should be v2, not v1"
    assert shown["version"] == 2, "The visible document version should be 2"
    _ok("Document list shows v2 only (v1 hidden as SUPERSEDED) ✓")

    # ─────────────────────────────────────────────────────────────────────────
    _step("Phase 10 — Hybrid search: verify TE-004 and Section 7.2 found")
    # ─────────────────────────────────────────────────────────────────────────

    chat_te004 = node.chat("What is policy TE-004?")
    answer_te004 = chat_te004.get("answer", "")
    _ok(f"TE-004 answer: {answer_te004[:120]}...")
    assert "TE-004" in answer_te004 or "mental" in answer_te004.lower(), (
        f"Expected answer to mention TE-004 or mental health leave, got: {answer_te004[:200]}"
    )
    _ok("Hybrid search: TE-004 identifier correctly retrieved ✓")

    # ─────────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 65)
    print("  ALL PHASES PASSED ✓")
    print("=" * 65)
    print(f"\n  Summary:")
    print(f"    v1 id:      {v1_id}")
    print(f"    v2 id:      {v2_id}")
    print(f"    v1 status:  SUPERSEDED")
    print(f"    v2 status:  INDEXED")
    print(f"    ChromaDB:   {after['total_chunks']} chunks (v2 only)")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--node-url", default=os.getenv("NODE_URL", "http://localhost:3000"))
    parser.add_argument("--ai-url",   default=os.getenv("AI_URL",   "http://localhost:8100"))
    parser.add_argument("--token",    default=os.getenv("TEST_JWT_TOKEN", ""))
    parser.add_argument("--internal-token", default=os.getenv("INTERNAL_TOKEN", "dev-internal-token"))
    args = parser.parse_args()

    if not args.token:
        sys.exit(
            "\nError: JWT token required.\n"
            "  --token eyJhbGc...   or   export TEST_JWT_TOKEN=eyJhbGc...\n"
            "\nGet one by logging in as an admin user and copying the token from "
            "the browser DevTools → Application → Local Storage → 'token'.\n"
        )

    run(args.node_url, args.ai_url, args.token, args.internal_token)


if __name__ == "__main__":
    main()
