"""Tests for secure retrieval — department scope must come from ctx, not body.

Security contract (enforced in app/api/v1/search.py):
  The department filter applied to ChromaDB MUST come from ctx.department
  (RequestContext, populated from X-User-Department header by the Node gateway),
  NOT from body.department (client-controlled).

This prevents an HR user from querying Finance documents by sending:
  POST /search { "department": "Finance" }

What MUST happen:
  JWT → Node gateway → X-User-Department: HR → AI service → ctx.department = HR
  body.department is silently ignored.

All tests monkeypatch RetrievalPipeline to capture the RetrievalConfig the
endpoint builds, so tests are fast and require no actual embedding/ChromaDB.
"""
from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.models.retrieval_result import RetrievalResult
from app.retrieval.retrieval_service import RetrievalConfig
from app.services.vector_service import VectorService, get_vector_service
from app.repositories.vector_repository import VectorRepository
from app.vectorstore.chroma_client import ChromaClient
from tests.conftest import INTERNAL_TOKEN

# ── Fixtures ──────────────────────────────────────────────────────────────────

_EMPTY_RESULT = RetrievalResult(
    query="test",
    chunks_found=0,
    context="",
    prompt="You are OptiAgent.",
    citations=[],
    context_token_count=0,
    results=[],
)


def _make_client(monkeypatch: pytest.MonkeyPatch) -> tuple[TestClient, list[RetrievalConfig]]:
    """Return a TestClient and a list that is populated with captured configs.

    RetrievalPipeline is patched to record the RetrievalConfig it receives
    without running the actual retrieval pipeline.
    """
    captured: list[RetrievalConfig] = []

    class _CapturingPipeline:
        def __init__(self, **kwargs: Any) -> None:
            pass

        async def run(self, _query: str, config: RetrievalConfig) -> RetrievalResult:
            captured.append(config)
            return _EMPTY_RESULT

    monkeypatch.setattr("app.api.v1.search.RetrievalPipeline", _CapturingPipeline)

    mem_client = ChromaClient(mode="memory")
    repo = VectorRepository(client=mem_client, collection_name="test_secure")
    vec_svc = VectorService(repo)

    app = create_app()
    app.dependency_overrides[get_vector_service] = lambda: vec_svc

    client = TestClient(app)
    return client, captured


# ── Header helpers ─────────────────────────────────────────────────────────────

def _headers(department: str | None = None, *, omit_dept: bool = False) -> dict[str, str]:
    """Build gateway headers, optionally overriding X-User-Department."""
    base = {
        "X-Internal-Token": INTERNAL_TOKEN,
        "X-User-Id": "u_test",
        "X-User-Role": "HR_MANAGER",
        "X-Tenant": "acme-corp",
    }
    if not omit_dept:
        if department is not None:
            base["X-User-Department"] = department
        else:
            base["X-User-Department"] = "HR"   # default to HR
    return base


# ── ctx.department enforcement ────────────────────────────────────────────────

class TestDepartmentFromContext:
    """The search config must use ctx.department, derived from the gateway header."""

    def test_hr_department_header_produces_hr_config(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        client, captured = _make_client(monkeypatch)
        client.post(
            "/api/v1/search",
            json={"query": "leave policy"},
            headers=_headers("HR"),
        )
        assert len(captured) == 1
        assert captured[0].department == "HR"

    def test_finance_department_header_produces_finance_config(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        client, captured = _make_client(monkeypatch)
        client.post(
            "/api/v1/search",
            json={"query": "expense claims"},
            headers=_headers("Finance"),
        )
        assert captured[0].department == "Finance"

    def test_it_department_header_produces_it_config(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        client, captured = _make_client(monkeypatch)
        client.post(
            "/api/v1/search",
            json={"query": "network access policy"},
            headers=_headers("IT"),
        )
        assert captured[0].department == "IT"

    def test_missing_dept_header_produces_none_config(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When no X-User-Department header is present, config.department = None.

        A None department means no department filter — the user sees all docs
        they have access to (which Node has already restricted via RBAC before
        this point).
        """
        client, captured = _make_client(monkeypatch)
        client.post(
            "/api/v1/search",
            json={"query": "general policy"},
            headers=_headers(omit_dept=True),
        )
        assert captured[0].department is None


# ── body.department is ignored ────────────────────────────────────────────────

class TestBodyDepartmentIgnored:
    """Supplying body.department must never override the gateway header scope."""

    def test_hr_user_cannot_escalate_to_finance_via_body(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """HR user sends body.department='Finance' → still scoped to HR."""
        client, captured = _make_client(monkeypatch)
        client.post(
            "/api/v1/search",
            json={"query": "expense claims", "department": "Finance"},  # body attempt
            headers=_headers("HR"),  # gateway says HR
        )
        assert captured[0].department == "HR"  # body was ignored

    def test_finance_user_cannot_escalate_to_hr_via_body(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Finance user sends body.department='HR' → still scoped to Finance."""
        client, captured = _make_client(monkeypatch)
        client.post(
            "/api/v1/search",
            json={"query": "leave policy", "department": "HR"},  # body attempt
            headers=_headers("Finance"),  # gateway says Finance
        )
        assert captured[0].department == "Finance"

    def test_body_department_ignored_when_header_absent(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """No dept header + body.department='Finance' → config.department=None.

        The body cannot inject a department filter when the gateway hasn't set one.
        """
        client, captured = _make_client(monkeypatch)
        client.post(
            "/api/v1/search",
            json={"query": "policy", "department": "Finance"},  # body attempt
            headers=_headers(omit_dept=True),   # no gateway header
        )
        assert captured[0].department is None  # body was ignored; no filter applied

    def test_null_body_department_does_not_override_header(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Sending body.department=null explicitly does not override gateway header."""
        client, captured = _make_client(monkeypatch)
        client.post(
            "/api/v1/search",
            json={"query": "policy", "department": None},  # explicit null
            headers=_headers("HR"),
        )
        assert captured[0].department == "HR"

    def test_omitting_body_department_uses_header(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When body.department is omitted (default None), header still applies."""
        client, captured = _make_client(monkeypatch)
        client.post(
            "/api/v1/search",
            json={"query": "policy"},  # no department field in body
            headers=_headers("HR"),
        )
        assert captured[0].department == "HR"


# ── use_hybrid flag wiring ────────────────────────────────────────────────────

class TestHybridFlagWiring:
    """use_hybrid from body is a feature flag, not a security concern.
    It should be passed through from body to config correctly.
    """

    def test_use_hybrid_defaults_to_true(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client, captured = _make_client(monkeypatch)
        client.post(
            "/api/v1/search",
            json={"query": "leave policy"},
            headers=_headers("HR"),
        )
        assert captured[0].use_hybrid is True

    def test_use_hybrid_false_is_respected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client, captured = _make_client(monkeypatch)
        client.post(
            "/api/v1/search",
            json={"query": "leave policy", "use_hybrid": False},
            headers=_headers("HR"),
        )
        assert captured[0].use_hybrid is False

    def test_use_hybrid_true_explicit_passes_through(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        client, captured = _make_client(monkeypatch)
        client.post(
            "/api/v1/search",
            json={"query": "leave policy", "use_hybrid": True},
            headers=_headers("HR"),
        )
        assert captured[0].use_hybrid is True


# ── Proof-of-concept: cross-department isolation ──────────────────────────────

class TestCrossDepartmentIsolation:
    """Demonstrate that two users from different departments get different scopes.

    These tests do NOT run actual retrieval — they confirm the config objects
    produced for two users have mutually exclusive department values.
    """

    def test_hr_and_finance_produce_different_scopes(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        client, captured = _make_client(monkeypatch)

        # HR user
        client.post(
            "/api/v1/search",
            json={"query": "leave policy"},
            headers=_headers("HR"),
        )
        # Finance user
        client.post(
            "/api/v1/search",
            json={"query": "expense claims"},
            headers=_headers("Finance"),
        )

        assert len(captured) == 2
        departments = {c.department for c in captured}
        assert departments == {"HR", "Finance"}
        # Confirm they never leaked into each other
        assert captured[0].department != captured[1].department

    def test_scope_is_request_isolated(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Each request carries only its own department scope — no state leaks."""
        client, captured = _make_client(monkeypatch)

        # Make 5 alternating requests
        depts = ["HR", "Finance", "IT", "HR", "Finance"]
        for dept in depts:
            client.post(
                "/api/v1/search",
                json={"query": "query"},
                headers=_headers(dept),
            )

        captured_depts = [c.department for c in captured]
        assert captured_depts == depts  # order and values match exactly
