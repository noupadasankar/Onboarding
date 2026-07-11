"""Shared pytest fixtures.

Sets required environment variables before any application module is imported
so that pydantic-settings finds INTERNAL_SERVICE_TOKEN and does not fail.
"""
import os

# Must be set before importing app modules (pydantic-settings reads at import).
os.environ.setdefault("INTERNAL_SERVICE_TOKEN", "test-token-for-pytest")

import pytest
from fastapi.testclient import TestClient

from app.main import create_app

INTERNAL_TOKEN: str = os.environ["INTERNAL_SERVICE_TOKEN"]

# Full set of headers the Node gateway forwards with every authenticated request.
GATEWAY_HEADERS: dict[str, str] = {
    "X-Internal-Token": INTERNAL_TOKEN,
    "X-User-Id": "u_test",
    "X-User-Role": "IT_ADMIN",
    "X-User-Department": "Engineering",
    "X-Tenant": "acme-corp",
    "X-Request-Id": "test-request-id-001",
}


@pytest.fixture(scope="session")
def client() -> TestClient:
    """A single TestClient reused across all tests in the session."""
    return TestClient(create_app())
