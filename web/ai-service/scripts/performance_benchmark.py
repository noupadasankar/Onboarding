#!/usr/bin/env python3
"""OptiAgent AI-service performance benchmark.

Measures latency for each stage of both pipelines:

  Ingestion pipeline:
    Upload → Chunk → Embed → ChromaDB upsert

  Query pipeline:
    Query embed → Dense search → BM25 build → RRF fusion → Rerank → Context

Usage:
  python scripts/performance_benchmark.py
  python scripts/performance_benchmark.py --ai-url http://localhost:8100
  python scripts/performance_benchmark.py --runs 10 --chunk-size 400

Environment:
  AI_URL          AI service base URL   (default: http://localhost:8100)
  INTERNAL_TOKEN  Shared secret         (default: dev-internal-token)
"""
from __future__ import annotations

import argparse
import io
import json
import os
import statistics
import sys
import time

try:
    import requests
    from fpdf import FPDF
except ImportError:
    sys.exit("Missing deps.  Run: pip install requests fpdf2")


# ── Document content ──────────────────────────────────────────────────────────

_HR_POLICY = """
Employee Handbook — HR Policies

1. Annual Leave
   All permanent employees receive 25 days of paid annual leave per year.
   Policy code HR-204 governs annual leave. Leave requests must be submitted
   at least two weeks in advance. Unused leave may be carried over subject
   to line manager approval (maximum 5 days carry-over).

2. Sick Leave
   Employees receive 10 sick days per calendar year without a GP note.
   Extended sick leave (>10 days) requires a fit note from a GP.

3. Mental Health Leave
   Policy TE-004: employees may take up to 3 mental health leave days per year.
   These are separate from sick leave and do not require medical documentation.

4. Maternity and Paternity Leave
   Statutory maternity pay applies for up to 39 weeks.
   Paternity leave: 2 weeks at full pay.

5. Hybrid Working
   Section 7.2: employees may work from home up to 3 days per week.
   Office attendance is required on Tuesdays and Thursdays.

6. Performance Reviews
   Annual reviews are conducted in Q1. Pay increases take effect in April.
   Mid-year check-ins are held in Q3.

7. Benefits
   BUPA medical insurance: £150 monthly employer contribution.
   Pension: 5% employee, 8% employer contribution.
   Cycle to Work scheme and season ticket loans available.

8. Training and Development
   Learning budget: £1,500 per employee per year.
   Mandatory compliance training must be completed by 31 March each year.
""" * 3  # repeat to create more chunks


def _make_pdf(text: str, pages: int = 3) -> bytes:
    pdf = FPDF()
    for _ in range(pages):
        pdf.add_page()
        pdf.set_font("Helvetica", size=10)
        for line in text.strip().split("\n"):
            pdf.multi_cell(0, 6, line)
    return bytes(pdf.output())


# ── HTTP client ───────────────────────────────────────────────────────────────

class Timer:
    """Context manager that records elapsed time in milliseconds."""
    def __init__(self) -> None:
        self.elapsed_ms: float = 0.0

    def __enter__(self) -> "Timer":
        self._start = time.perf_counter()
        return self

    def __exit__(self, *args: object) -> None:
        self.elapsed_ms = (time.perf_counter() - self._start) * 1000.0


class AiClient:
    def __init__(self, base_url: str, internal_token: str) -> None:
        self.base = base_url.rstrip("/")
        self.s = requests.Session()
        self.s.headers.update({
            "X-Internal-Token": internal_token,
            "X-User-Id": "bench",
            "X-User-Role": "IT_ADMIN",
            "X-User-Department": "HR",
        })

    def upload(self, pdf: bytes, filename: str = "bench_handbook.pdf") -> tuple[str, float]:
        """Upload a document; return (document_id, latency_ms)."""
        with Timer() as t:
            res = self.s.post(
                f"{self.base}/api/v1/documents/upload",
                files={"file": (filename, io.BytesIO(pdf), "application/pdf")},
            )
            res.raise_for_status()
        return res.json()["document_id"], t.elapsed_ms

    def index(self, doc_id: str, chunk_size: int = 400, overlap: int = 60) -> tuple[dict, float]:
        """Run index pipeline; return (result, latency_ms)."""
        with Timer() as t:
            res = self.s.post(
                f"{self.base}/api/v1/documents/{doc_id}/index"
                f"?chunk_size={chunk_size}&overlap={overlap}&min_tokens=20",
            )
            res.raise_for_status()
        return res.json(), t.elapsed_ms

    def search(
        self, query: str, use_hybrid: bool = True, top_k: int = 5
    ) -> tuple[dict, float]:
        """Run retrieval; return (result, latency_ms)."""
        with Timer() as t:
            res = self.s.post(
                f"{self.base}/api/v1/search",
                json={"query": query, "use_hybrid": use_hybrid, "top_k": top_k},
            )
            res.raise_for_status()
        return res.json(), t.elapsed_ms

    def delete_vectors(self, doc_id: str) -> None:
        self.s.delete(f"{self.base}/api/v1/documents/{doc_id}/vectors")

    def health(self) -> dict:
        return self.s.get(f"{self.base}/health").json()

    def vector_count(self) -> dict:
        return self.s.get(f"{self.base}/api/v1/vectorstore/count").json()


# ── Formatting ────────────────────────────────────────────────────────────────

def _row(label: str, ms: float, note: str = "") -> None:
    bar_len = min(40, int(ms / 25))
    bar = "█" * bar_len
    note_str = f"  ({note})" if note else ""
    print(f"  {label:<35} {ms:>8.1f} ms  {bar}{note_str}")


def _section(title: str) -> None:
    print(f"\n  {'─' * 60}")
    print(f"  {title}")
    print(f"  {'─' * 60}")


def _stats(values: list[float]) -> str:
    if not values:
        return "n/a"
    return (
        f"min={min(values):.0f}ms  "
        f"mean={statistics.mean(values):.0f}ms  "
        f"p95={sorted(values)[int(len(values) * 0.95)]:.0f}ms  "
        f"max={max(values):.0f}ms"
    )


# ── Benchmark ────────────────────────────────────────────────────────────────

SEARCH_QUERIES = [
    ("Semantic — broad", "How many days of annual leave do employees receive?", True),
    ("Keyword — HR-204", "HR-204", True),
    ("Keyword — TE-004", "TE-004", True),
    ("Keyword — BUPA",   "BUPA insurance contribution", True),
    ("Keyword — £150",   "£150 monthly", True),
    ("Keyword — 7.2",    "Section 7.2 hybrid working", True),
    ("Dense only — HR-204",  "HR-204", False),
    ("Dense only — BUPA",    "BUPA", False),
]


def run(
    ai_url: str,
    internal_token: str,
    runs: int,
    chunk_size: int,
) -> None:
    client = AiClient(ai_url, internal_token)

    print("\n" + "=" * 65)
    print("  OptiAgent — AI Service Performance Benchmark")
    print("=" * 65)
    print(f"  Target:      {ai_url}")
    print(f"  Search runs: {runs}")
    print(f"  Chunk size:  {chunk_size}")

    # ── Health check ──────────────────────────────────────────────────────────
    try:
        health = client.health()
        print(f"  Health:      {health.get('status', 'unknown')}")
    except Exception as exc:
        sys.exit(f"\n  Cannot reach AI service at {ai_url}: {exc}\n")

    # ── Ingestion pipeline ─────────────────────────────────────────────────────
    _section("INGESTION PIPELINE")

    pdf = _make_pdf(_HR_POLICY, pages=3)
    print(f"  Document:    {len(pdf) / 1024:.1f} KB PDF ({_HR_POLICY.count(chr(10))} lines)")

    # Upload
    doc_id, upload_ms = client.upload(pdf)
    _row("Upload (network + disk write)", upload_ms)

    # Index (chunking + embedding + ChromaDB upsert)
    with Timer() as t_total:
        idx_result, idx_ms = client.index(doc_id, chunk_size=chunk_size)
    chunks   = idx_result.get("chunks_indexed", "?")
    provider = idx_result.get("provider", "?")
    model    = idx_result.get("model", "?")
    _row(f"Index pipeline ({chunks} chunks)", idx_ms, f"{provider}/{model}")
    _row("  ≈ chunk + clean + embed + upsert", idx_ms, "combined")

    count = client.vector_count()
    print(f"\n  ChromaDB: {count['total_chunks']} chunks, "
          f"{count['unique_documents']} document(s)")

    ingestion_total = upload_ms + idx_ms
    print(f"\n  Total ingestion latency: {ingestion_total:.1f} ms")

    # ── Query pipeline ─────────────────────────────────────────────────────────
    _section("QUERY PIPELINE (RETRIEVAL ONLY — no LLM)")

    all_hybrid_ms: list[float] = []
    all_dense_ms:  list[float] = []

    # Warm up (first call may be slower due to BM25 index build)
    print("\n  [warm-up]")
    client.search("annual leave policy", use_hybrid=True)
    client.search("annual leave policy", use_hybrid=False)

    print(f"\n  {'Query':<38} {'Hybrid':>10}  {'Dense-only':>10}  {'Delta':>10}")
    print(f"  {'─'*38} {'─'*10}  {'─'*10}  {'─'*10}")

    for label, query, _ in SEARCH_QUERIES:
        hybrid_times = []
        dense_times  = []
        for _ in range(runs):
            _, h_ms = client.search(query, use_hybrid=True)
            _, d_ms = client.search(query, use_hybrid=False)
            hybrid_times.append(h_ms)
            dense_times.append(d_ms)
        h_mean = statistics.mean(hybrid_times)
        d_mean = statistics.mean(dense_times)
        delta  = h_mean - d_mean
        all_hybrid_ms.extend(hybrid_times)
        all_dense_ms.extend(dense_times)

        sign = "+" if delta > 0 else ""
        print(f"  {label:<38} {h_mean:>9.1f}ms  {d_mean:>9.1f}ms  {sign}{delta:>8.1f}ms")

    print(f"\n  Hybrid search stats  ({runs} runs × {len(SEARCH_QUERIES)} queries):")
    print(f"    {_stats(all_hybrid_ms)}")
    print(f"\n  Dense-only stats:")
    print(f"    {_stats(all_dense_ms)}")

    overhead_mean = statistics.mean(all_hybrid_ms) - statistics.mean(all_dense_ms)
    print(f"\n  BM25+RRF overhead: {overhead_mean:+.1f} ms average per query")
    print(f"  (BM25 index is built from ChromaDB corpus at query time)")

    # ── Keyword recall spot-check ─────────────────────────────────────────────
    _section("KEYWORD RECALL SPOT-CHECK")
    spot_queries = [
        ("HR-204", "hr204"),
        ("TE-004", "te004"),
        ("BUPA",   "bupa"),
        ("£150",   "gbp150"),
        ("Section 7.2", "section72"),
    ]

    print(f"\n  {'Query':<20} {'Hybrid top chunk':>45}  {'Dense top chunk':>45}")
    print(f"  {'─'*20} {'─'*45}  {'─'*45}")
    for query, _ in spot_queries:
        h_result, _ = client.search(query, use_hybrid=True, top_k=1)
        d_result, _ = client.search(query, use_hybrid=False, top_k=1)
        h_ctx = (h_result.get("context") or "—")[:43]
        d_ctx = (d_result.get("context") or "—")[:43]
        print(f"  {query:<20} {h_ctx:>45}  {d_ctx:>45}")

    # ── Cleanup ──────────────────────────────────────────────────────────────
    _section("CLEANUP")
    client.delete_vectors(doc_id)
    count_after = client.vector_count()
    print(f"  Deleted vectors for benchmark document.")
    print(f"  ChromaDB: {count_after['total_chunks']} chunks remaining.")

    # ── Summary ──────────────────────────────────────────────────────────────
    _section("SUMMARY TABLE")
    rows = [
        ("Upload",           upload_ms,                    "network + disk write"),
        ("Index pipeline",   idx_ms,                       f"{chunks} chunks, embed + upsert"),
        ("Retrieval (dense-only)",  statistics.mean(all_dense_ms), "embed + ChromaDB query + rerank"),
        ("Retrieval (hybrid)",      statistics.mean(all_hybrid_ms),"+ BM25 build + RRF fusion"),
        ("Hybrid overhead",  overhead_mean,                "BM25 + RRF added cost"),
    ]
    print()
    for label, ms, note in rows:
        _row(label, ms, note)

    print(f"\n  Benchmark complete.\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--ai-url",
        default=os.getenv("AI_URL", "http://localhost:8100"),
    )
    parser.add_argument(
        "--internal-token",
        default=os.getenv("INTERNAL_TOKEN", "dev-internal-token"),
    )
    parser.add_argument("--runs",       type=int, default=5, help="Queries per run (default: 5)")
    parser.add_argument("--chunk-size", type=int, default=400, help="Chunk size (default: 400)")
    args = parser.parse_args()
    run(args.ai_url, args.internal_token, args.runs, args.chunk_size)


if __name__ == "__main__":
    main()
