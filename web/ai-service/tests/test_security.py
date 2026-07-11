"""Tests for internal authentication and request context assembly.

Validates the full gateway trust contract:
  - Token validation (401 on missing/wrong token)
  - Context assembly (400 on missing required headers)
  - Optional headers handled gracefully (department, tenant, request_id)
  - Chat placeholder endpoint requires a valid authenticated request
"""
from fastapi.testclient import TestClient

from tests.conftest import GATEWAY_HEADERS, INTERNAL_TOKEN


class TestInternalTokenValidation:
    """The internal token is the sole authentication mechanism for the AI service."""

    def test_valid_token_accepted(self, client: TestClient) -> None:
        res = client.get("/api/v1/whoami", headers=GATEWAY_HEADERS)
        assert res.status_code == 200

    def test_missing_token_returns_401(self, client: TestClient) -> None:
        headers = {k: v for k, v in GATEWAY_HEADERS.items() if k != "X-Internal-Token"}
        res = client.get("/api/v1/whoami", headers=headers)
        assert res.status_code == 401

    def test_wrong_token_returns_401(self, client: TestClient) -> None:
        headers = {**GATEWAY_HEADERS, "X-Internal-Token": "not-the-real-token"}
        res = client.get("/api/v1/whoami", headers=headers)
        assert res.status_code == 401

    def test_empty_string_token_returns_401(self, client: TestClient) -> None:
        headers = {**GATEWAY_HEADERS, "X-Internal-Token": ""}
        res = client.get("/api/v1/whoami", headers=headers)
        assert res.status_code == 401

    def test_almost_correct_token_returns_401(self, client: TestClient) -> None:
        tampered = INTERNAL_TOKEN[:-1] + ("x" if INTERNAL_TOKEN[-1] != "x" else "y")
        headers = {**GATEWAY_HEADERS, "X-Internal-Token": tampered}
        res = client.get("/api/v1/whoami", headers=headers)
        assert res.status_code == 401


class TestRequestContextAssembly:
    """RequestContext is built from forwarded headers after token validation passes."""

    def test_full_context_returned(self, client: TestClient) -> None:
        res = client.get("/api/v1/whoami", headers=GATEWAY_HEADERS)
        assert res.status_code == 200
        ctx = res.json()
        assert ctx["user_id"] == "u_test"
        assert ctx["role"] == "IT_ADMIN"
        assert ctx["department"] == "Engineering"
        assert ctx["tenant"] == "acme-corp"
        assert ctx["request_id"] == "test-request-id-001"

    def test_missing_user_id_returns_400(self, client: TestClient) -> None:
        headers = {k: v for k, v in GATEWAY_HEADERS.items() if k != "X-User-Id"}
        res = client.get("/api/v1/whoami", headers=headers)
        assert res.status_code == 400

    def test_missing_role_returns_400(self, client: TestClient) -> None:
        headers = {k: v for k, v in GATEWAY_HEADERS.items() if k != "X-User-Role"}
        res = client.get("/api/v1/whoami", headers=headers)
        assert res.status_code == 400

    def test_missing_user_id_and_role_returns_400(self, client: TestClient) -> None:
        headers = {"X-Internal-Token": INTERNAL_TOKEN}
        res = client.get("/api/v1/whoami", headers=headers)
        assert res.status_code == 400

    def test_department_is_optional(self, client: TestClient) -> None:
        headers = {k: v for k, v in GATEWAY_HEADERS.items() if k != "X-User-Department"}
        res = client.get("/api/v1/whoami", headers=headers)
        assert res.status_code == 200
        assert res.json()["department"] is None

    def test_tenant_defaults_to_default_when_absent(self, client: TestClient) -> None:
        headers = {k: v for k, v in GATEWAY_HEADERS.items() if k != "X-Tenant"}
        res = client.get("/api/v1/whoami", headers=headers)
        assert res.status_code == 200
        assert res.json()["tenant"] == "default"

    def test_request_id_forwarded_into_context(self, client: TestClient) -> None:
        headers = {**GATEWAY_HEADERS, "X-Request-Id": "my-correlation-id"}
        res = client.get("/api/v1/whoami", headers=headers)
        assert res.status_code == 200
        assert res.json()["request_id"] == "my-correlation-id"

    def test_request_id_empty_string_when_absent(self, client: TestClient) -> None:
        headers = {k: v for k, v in GATEWAY_HEADERS.items() if k != "X-Request-Id"}
        res = client.get("/api/v1/whoami", headers=headers)
        assert res.status_code == 200
        assert res.json()["request_id"] == ""


class TestChatEndpoint:
    """Chat placeholder validates the full authenticated request pattern."""

    def test_chat_requires_internal_token(self, client: TestClient) -> None:
        res = client.post("/api/v1/chat", json={"message": "hello"})
        assert res.status_code == 401

    def test_chat_requires_user_context(self, client: TestClient) -> None:
        res = client.post(
            "/api/v1/chat",
            json={"message": "hello"},
            headers={"X-Internal-Token": INTERNAL_TOKEN},
        )
        assert res.status_code == 400

    def test_chat_returns_placeholder_message(self, client: TestClient) -> None:
        res = client.post(
            "/api/v1/chat",
            json={"message": "What is the leave policy?"},
            headers=GATEWAY_HEADERS,
        )
        assert res.status_code == 200
        data = res.json()
        assert "message" in data
        assert len(data["message"]) > 0

    def test_chat_echoes_user_id_and_role(self, client: TestClient) -> None:
        res = client.post(
            "/api/v1/chat",
            json={"message": "Summarise the HR handbook."},
            headers=GATEWAY_HEADERS,
        )
        assert res.status_code == 200
        data = res.json()
        assert data["user_id"] == "u_test"
        assert data["role"] == "IT_ADMIN"

    def test_chat_rejects_empty_message(self, client: TestClient) -> None:
        res = client.post(
            "/api/v1/chat",
            json={"message": ""},
            headers=GATEWAY_HEADERS,
        )
        assert res.status_code == 422
