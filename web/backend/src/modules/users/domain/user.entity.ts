/**
 * User domain entity — framework-free. Repositories map persistence rows to this
 * shape; services and controllers work only with it (never with Prisma models).
 */
import type { AuthUser, Permission, Role, UserDTO } from '@hr-onboarding/shared';
import { permissionsForRole } from '@hr-onboarding/shared';

export interface UserProps {
  id: string;
  email: string;
  passwordHash: string;
  department: string | null;
  isActive: boolean;
  role: Role;
  createdAt: Date;
}

export class UserEntity {
  constructor(readonly props: UserProps) {}

  get id(): string {
    return this.props.id;
  }
  get email(): string {
    return this.props.email;
  }
  get passwordHash(): string {
    return this.props.passwordHash;
  }
  get department(): string | null {
    return this.props.department;
  }
  get isActive(): boolean {
    return this.props.isActive;
  }
  get role(): Role {
    return this.props.role;
  }
  get permissions(): Permission[] {
    return [...permissionsForRole(this.props.role)];
  }

  /** Client-safe projection (no password hash). */
  toAuthUser(): AuthUser {
    return {
      id: this.id,
      email: this.email,
      role: this.role,
      department: this.department,
      permissions: this.permissions,
    };
  }

  /** Admin list/detail projection — includes isActive and createdAt, no permissions. */
  toUserDTO(): UserDTO {
    return {
      id: this.id,
      email: this.email,
      role: this.role,
      department: this.department,
      isActive: this.isActive,
      createdAt: this.props.createdAt.toISOString(),
    };
  }
}
