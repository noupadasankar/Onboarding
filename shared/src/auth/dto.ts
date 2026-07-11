/**
 * Data-transfer objects. Wire contracts between the React frontend and the Node
 * backend — defined once, imported by both, so types can never drift.
 */
import type { Permission, Role } from './roles.js';

/** Credentials submitted to `POST /auth/login`. */
export interface LoginRequest {
  email: string;
  password: string;
}

/** Payload for creating a user (admin-gated, requires users:write). */
export interface RegisterRequest {
  email: string;
  password: string;
  role: Role;
  department?: string;
}

/** Alias — CreateUserRequest and RegisterRequest are structurally identical. */
export type CreateUserRequest = RegisterRequest;

/** Body for PATCH /users/:id — all fields optional. */
export interface UpdateUserRequest {
  role?: Role;
  department?: string | null;
  isActive?: boolean;
}

/** Admin-safe user projection returned by user management endpoints. */
export interface UserDTO {
  id: string;
  email: string;
  role: Role;
  department: string | null;
  isActive: boolean;
  createdAt: string;
}

/** Role catalog entry — used by GET /roles for frontend dropdowns. */
export interface RoleDTO {
  name: Role;
  permissions: Permission[];
}

/** Access + refresh token pair returned by login / refresh. */
export interface TokenPair {
  accessToken: string;
  /** Seconds until the access token expires (client schedules a refresh). */
  expiresIn: number;
  refreshToken: string;
}

/** The authenticated principal, safe to expose to the client (no secrets). */
export interface AuthUser {
  id: string;
  email: string;
  role: Role;
  department: string | null;
  permissions: Permission[];
}

/** Response of `POST /auth/login` and `POST /auth/refresh`. */
export interface AuthResponse {
  user: AuthUser;
  tokens: TokenPair;
}

/** Body of `POST /auth/refresh`. */
export interface RefreshRequest {
  refreshToken: string;
}

/**
 * JWT access-token claims. Kept intentionally small — the gateway forwards
 * `sub` (userId) and `role` to the AI service; permissions are re-derived
 * server-side rather than trusted from the token body where cheap to do so.
 */
export interface AccessTokenClaims {
  sub: string;
  email: string;
  role: Role;
  type: 'access';
}

/** JWT refresh-token claims. `jti` lets us rotate/blacklist individual tokens. */
export interface RefreshTokenClaims {
  sub: string;
  jti: string;
  type: 'refresh';
}
