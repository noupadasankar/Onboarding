# Users API

OptiAgent REST API — `/api/v1/users` and `/api/v1/roles`

---

## Overview

The users endpoints provide CRUD operations for user accounts, role management, and permission listings. All endpoints require authentication. Most write operations additionally require specific permissions.

All responses use the shared `ApiResponse` envelope. Paginated endpoints return a `PaginatedResponse<T>` in the `data` field.

### ApiResponse Envelope

```json
{ "success": true,  "data": <T> }
{ "success": false, "error": { "code": "...", "message": "..." } }
```

### PaginatedResponse

```typescript
{
  items:      T[];
  total:      number;   // Total matching records across all pages
  page:       number;   // Current page (1-indexed)
  pageSize:   number;   // Items per page
  totalPages: number;
}
```

---

## Schemas

### UserDTO

```typescript
{
  id:          string;
  email:       string;
  displayName: string;
  firstName:   string;
  lastName:    string;
  roles:       RoleDTO[];
  permissions: string[];
  isActive:    boolean;
  createdAt:   string;   // ISO 8601
  updatedAt:   string;   // ISO 8601
}
```

### RoleDTO

```typescript
{
  id:          string;
  name:        string;   // e.g. "HR_MANAGER"
  displayName: string;   // e.g. "HR Manager"
  permissions: string[];
}
```

### CreateUserRequest

```typescript
{
  email:       string;   // Unique, valid email
  password:    string;   // Min 8 chars, must include letter and number
  firstName:   string;   // Required
  lastName:    string;   // Required
  displayName?: string;  // Defaults to "firstName lastName"
  roleIds:     string[]; // At least one role required
}
```

### UpdateUserRequest

```typescript
{
  firstName?:   string;
  lastName?:    string;
  displayName?: string;
  roleIds?:     string[];
  isActive?:    boolean;
}
```

---

## Endpoints

---

### GET /api/v1/users

Returns a paginated, filtered list of users.

**Authentication required:** Yes
**Permission required:** `users:read`

**Query parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `page` | number | No | Page number, 1-indexed. Default: `1` |
| `pageSize` | number | No | Items per page. Default: `20`, max: `100` |
| `search` | string | No | Partial match on `email`, `firstName`, `lastName`, or `displayName` |
| `role` | string | No | Filter by role name (e.g. `HR_MANAGER`) |
| `isActive` | boolean | No | Filter by active status. Omit to return all |

**Response:** `ApiResponse<PaginatedResponse<UserDTO>>` — HTTP 200

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id":          "usr_01HZXK9...",
        "email":       "jane.doe@optiagent.com",
        "displayName": "Jane Doe",
        "firstName":   "Jane",
        "lastName":    "Doe",
        "roles":       [{ "id": "role_...", "name": "HR_MANAGER", "displayName": "HR Manager", "permissions": ["users:read"] }],
        "permissions": ["users:read"],
        "isActive":    true,
        "createdAt":   "2026-01-15T09:00:00.000Z",
        "updatedAt":   "2026-01-15T09:00:00.000Z"
      }
    ],
    "total":      42,
    "page":        1,
    "pageSize":   20,
    "totalPages":  3
  }
}
```

**Error responses:**

| HTTP | Code | Condition |
|---|---|---|
| 400 | `VALIDATION_ERROR` | Invalid query parameter types |
| 401 | `INVALID_TOKEN` | Missing or expired token |
| 403 | `PERMISSION_DENIED` | Caller does not hold `users:read` |

---

### GET /api/v1/users/me

Returns the currently authenticated user's full profile. Equivalent to `GET /auth/me` but returns `UserDTO` (with role objects) rather than the leaner `AuthUser`.

**Authentication required:** Yes
**Permission required:** None (any authenticated user)

**Response:** `ApiResponse<UserDTO>` — HTTP 200

**Error responses:**

| HTTP | Code | Condition |
|---|---|---|
| 401 | `INVALID_TOKEN` | Missing or expired token |

---

### GET /api/v1/users/:id

Returns a single user by ID.

**Authentication required:** Yes
**Permission required:** `users:read`

**Path parameters:**

| Parameter | Type | Description |
|---|---|---|
| `id` | string | User ID |

**Response:** `ApiResponse<UserDTO>` — HTTP 200

**Error responses:**

| HTTP | Code | Condition |
|---|---|---|
| 401 | `INVALID_TOKEN` | Missing or expired token |
| 403 | `PERMISSION_DENIED` | Caller does not hold `users:read` |
| 404 | `USER_NOT_FOUND` | No user with the given ID |

---

### POST /api/v1/users

Creates a new user account.

**Authentication required:** Yes
**Permission required:** `users:write`

**Request body:** `CreateUserRequest`

```json
{
  "email":       "john.smith@optiagent.com",
  "password":    "SecurePass123!",
  "firstName":   "John",
  "lastName":    "Smith",
  "displayName": "John Smith",
  "roleIds":     ["role_01HZ..."]
}
```

**Response:** `ApiResponse<UserDTO>` — HTTP 201

**Error responses:**

| HTTP | Code | Condition |
|---|---|---|
| 400 | `VALIDATION_ERROR` | Request body fails schema validation |
| 401 | `INVALID_TOKEN` | Missing or expired token |
| 403 | `PERMISSION_DENIED` | Caller does not hold `users:write` |
| 409 | `EMAIL_ALREADY_EXISTS` | A user with this email already exists |

**Notes:**
- Creating a user generates an audit log entry with action `USER_CREATED`.
- The user's initial password is hashed with bcrypt (cost factor 12) before storage.

---

### PATCH /api/v1/users/:id

Updates one or more fields of an existing user. Fields not included in the request body are left unchanged.

**Authentication required:** Yes
**Permission required:** `users:write`

**Path parameters:**

| Parameter | Type | Description |
|---|---|---|
| `id` | string | User ID |

**Request body:** `UpdateUserRequest` (all fields optional)

```json
{
  "displayName": "Jane A. Doe",
  "roleIds":     ["role_01HZ...", "role_02HZ..."],
  "isActive":    false
}
```

**Response:** `ApiResponse<UserDTO>` — HTTP 200

**Error responses:**

| HTTP | Code | Condition |
|---|---|---|
| 400 | `VALIDATION_ERROR` | Request body fails schema validation |
| 401 | `INVALID_TOKEN` | Missing or expired token |
| 403 | `PERMISSION_DENIED` | Caller does not hold `users:write` |
| 404 | `USER_NOT_FOUND` | No user with the given ID |

**Notes:**
- Updating a user generates an audit log entry with action `USER_UPDATED`.
- Setting `isActive: false` deactivates the user but does not delete them.
- Changing `roleIds` replaces the user's role set entirely (not additive). Send all desired role IDs.

---

### DELETE /api/v1/users/:id

Deactivates a user account. Users are never hard-deleted; this operation sets `isActive: false`.

**Authentication required:** Yes
**Permission required:** `users:delete`

**Path parameters:**

| Parameter | Type | Description |
|---|---|---|
| `id` | string | User ID |

**Response:** `ApiResponse<{ deactivated: true }>` — HTTP 200

```json
{
  "success": true,
  "data": {
    "deactivated": true
  }
}
```

**Error responses:**

| HTTP | Code | Condition |
|---|---|---|
| 401 | `INVALID_TOKEN` | Missing or expired token |
| 403 | `PERMISSION_DENIED` | Caller does not hold `users:delete` |
| 403 | `CANNOT_DEACTIVATE_SELF` | A user cannot deactivate their own account |
| 404 | `USER_NOT_FOUND` | No user with the given ID |

**Notes:**
- Deactivating a user generates an audit log entry with action `USER_DEACTIVATED`.
- A deactivated user's existing access tokens are not immediately invalidated (they expire naturally). However, their refresh token is revoked in Redis, preventing further silent refreshes.

---

### GET /api/v1/roles

Returns all available roles and their associated permissions.

**Authentication required:** Yes
**Permission required:** `roles:read`

**Response:** `ApiResponse<RoleDTO[]>` — HTTP 200

```json
{
  "success": true,
  "data": [
    {
      "id":          "role_01HZ...",
      "name":        "ADMIN",
      "displayName": "Administrator",
      "permissions": ["users:read", "users:write", "users:delete", "roles:read", "roles:write", "permissions:read", "permissions:write", "audit:read", "ai:query"]
    },
    {
      "id":          "role_02HZ...",
      "name":        "HR_MANAGER",
      "displayName": "HR Manager",
      "permissions": ["users:read", "ai:query"]
    }
  ]
}
```

**Error responses:**

| HTTP | Code | Condition |
|---|---|---|
| 401 | `INVALID_TOKEN` | Missing or expired token |
| 403 | `PERMISSION_DENIED` | Caller does not hold `roles:read` |

---

### GET /api/v1/permissions

Returns the full list of permission strings defined in the system.

**Authentication required:** Yes
**Permission required:** `permissions:read`

**Response:** `ApiResponse<string[]>` — HTTP 200

```json
{
  "success": true,
  "data": [
    "ai:query",
    "audit:read",
    "permissions:read",
    "permissions:write",
    "roles:read",
    "roles:write",
    "users:delete",
    "users:read",
    "users:write"
  ]
}
```

**Error responses:**

| HTTP | Code | Condition |
|---|---|---|
| 401 | `INVALID_TOKEN` | Missing or expired token |
| 403 | `PERMISSION_DENIED` | Caller does not hold `permissions:read` |

**Notes:**
- The permission list is static and sourced from the shared `@optiagent/shared` package. It does not change at runtime.
- This endpoint is primarily used by the admin UI to populate permission assignment forms.
