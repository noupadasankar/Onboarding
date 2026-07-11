"""Shared constants. No logic, no imports from application modules."""

# ── Service identity ──────────────────────────────────────────────────────────
SERVICE_NAME = "ai-service"
API_V1_PREFIX = "/api/v1"

# ── HTTP headers forwarded by the Node gateway ────────────────────────────────
HEADER_INTERNAL_TOKEN = "X-Internal-Token"
HEADER_USER_ID = "X-User-Id"
HEADER_USER_ROLE = "X-User-Role"
HEADER_USER_DEPARTMENT = "X-User-Department"
HEADER_TENANT = "X-Tenant"
HEADER_REQUEST_ID = "X-Request-Id"
