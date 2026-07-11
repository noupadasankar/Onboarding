/**
 * Role-Based Access Control (RBAC) contract.
 *
 * This is the single source of truth for roles and permissions, shared by the
 * frontend (to gate UI) and the backend (to enforce access). The database seeds
 * from this map, so there is exactly one definition of "what a role can do".
 */

/** The four platform roles (matches the capstone spec §1.3, point 7). */
export enum Role {
  EMPLOYEE = 'EMPLOYEE',
  HR_MANAGER = 'HR_MANAGER',
  FINANCE_ADMIN = 'FINANCE_ADMIN',
  IT_ADMIN = 'IT_ADMIN',
}

/**
 * Fine-grained permissions. Access is checked against permissions, never roles
 * directly — this keeps authorization decoupled from the role taxonomy so new
 * roles can be introduced without touching guard code.
 *
 * Naming convention: `<resource>:<action>`.
 */
export enum Permission {
  // Users / identity
  USERS_READ = 'users:read',
  USERS_WRITE = 'users:write',
  USERS_MANAGE = 'users:manage',

  // Documents
  DOCUMENTS_UPLOAD = 'documents:upload',
  DOCUMENTS_MANAGE = 'documents:manage',

  // Agent domains (used from later increments; declared here so RBAC is stable)
  HR_QUERY = 'hr:query',
  FINANCE_QUERY = 'finance:query',
  IT_QUERY = 'it:query',

  // Governance
  GOVERNANCE_READ = 'governance:read',
  GOVERNANCE_OVERRIDE = 'governance:override',
}

/** Immutable role → permission grants. */
export const ROLE_PERMISSIONS: Readonly<Record<Role, readonly Permission[]>> = {
  [Role.EMPLOYEE]: [
    Permission.HR_QUERY,
    Permission.IT_QUERY,
    Permission.DOCUMENTS_UPLOAD,
  ],
  [Role.HR_MANAGER]: [
    Permission.USERS_READ,
    Permission.USERS_MANAGE,
    Permission.HR_QUERY,
    Permission.IT_QUERY,
    Permission.DOCUMENTS_UPLOAD,
    Permission.DOCUMENTS_MANAGE,
    Permission.GOVERNANCE_READ,
    Permission.GOVERNANCE_OVERRIDE,
  ],
  [Role.FINANCE_ADMIN]: [
    Permission.USERS_READ,
    Permission.FINANCE_QUERY,
    Permission.IT_QUERY,
    Permission.DOCUMENTS_UPLOAD,
    Permission.DOCUMENTS_MANAGE,
    Permission.GOVERNANCE_READ,
  ],
  [Role.IT_ADMIN]: [
    Permission.USERS_READ,
    Permission.USERS_WRITE,
    Permission.USERS_MANAGE,
    Permission.IT_QUERY,
    Permission.DOCUMENTS_UPLOAD,
    Permission.DOCUMENTS_MANAGE,
    Permission.GOVERNANCE_READ,
  ],
} as const;

/** All roles as an array — handy for seeds, validation and UI. */
export const ALL_ROLES: readonly Role[] = Object.values(Role);

/** All permissions as an array. */
export const ALL_PERMISSIONS: readonly Permission[] = Object.values(Permission);

/** Resolve the permission set granted to a role. */
export function permissionsForRole(role: Role): readonly Permission[] {
  return ROLE_PERMISSIONS[role] ?? [];
}

/** True when the given role has been granted `permission`. */
export function roleHasPermission(role: Role, permission: Permission): boolean {
  return permissionsForRole(role).includes(permission);
}
