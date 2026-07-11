"""Tests for the health, liveness, and readiness probes.

All three endpoints must be public (no token required).
The /whoami endpoint tests the gateway trust contract.
"""
from fastapi.testclient import TestClient

from tests.conftest import GATEWAY_HEADERS, INTERNAL_TOKEN


class TestHealthProbes:
    def test_health_returns_ok(self, client: TestClient) -> None:
        res = client.get("/api/v1/health")
        assert res.status_code == 200
        assert res.json() == {"status": "ok", "service": "ai-service"}

    def test_liveness_returns_alive(self, client: TestClient) -> None:
        res = client.get("/api/v1/live")
        assert res.status_code == 200
        assert res.json()["status"] == "alive"

    def test_readiness_returns_ready(self, client: TestClient) -> None:
        res = client.get("/api/v1/ready")
        assert res.status_code == 200
        assert res.json()["status"] == "ready"

    def test_health_x_request_id_echoed(self, client: TestClient) -> None:
        res = client.get("/api/v1/health", headers={"X-Request-Id": "trace-123"})
        assert res.headers.get("x-request-id") == "trace-123"

    def test_health_generates_request_id_when_absent(self, client: TestClient) -> None:
        res = client.get("/api/v1/health")
        assert "x-request-id" in res.headers


class TestGatewayTrust:
    def test_whoami_rejects_missing_token(self, client: TestClient) -> None:
        res = client.get("/api/v1/whoami")
        assert res.status_code == 401

    def test_whoami_rejects_wrong_token(self, client: TestClient) -> None:
        res = client.get(
            "/api/v1/whoami",
            headers={"X-Internal-Token": "bad-token", "X-User-Id": "u1", "X-User-Role": "EMPLOYEE"},
        )
        assert res.status_code == 401

    def test_whoami_requires_user_context_headers(self, client: TestClient) -> None:
        res = client.get("/api/v1/whoami", headers={"X-Internal-Token": INTERNAL_TOKEN})
        assert res.status_code == 400

    def test_whoami_trusts_gateway_forwarded_identity(self, client: TestClient) -> None:
        res = client.get("/api/v1/whoami", headers=GATEWAY_HEADERS)
        assert res.status_code == 200
        data = res.json()
        assert data["user_id"] == "u_test"
        assert data["role"] == "IT_ADMIN"
        assert data["department"] == "Engineering"
        assert data["tenant"] == "acme-corp"
        assert data["request_id"] == "test-request-id-001"
