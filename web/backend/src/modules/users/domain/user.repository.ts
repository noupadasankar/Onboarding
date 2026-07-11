/**
 * Repository interface (port). Services depend on this abstraction; the Prisma
 * implementation is an infrastructure detail bound via DI. This is what makes the
 * data layer swappable and the services unit-testable with a mock.
 */
import type { Role } from '@optiagent/shared';
import type { Paginated } from '@optiagent/shared';
import type { UserEntity } from './user.entity';

export interface CreateUserData {
  email: string;
  passwordHash: string;
  role: Role;
  department?: string | null;
}

export interface UpdateUserData {
  role?: Role;
  department?: string | null;
  isActive?: boolean;
}

export interface UserListFilters {
  search?: string;
  role?: Role;
  isActive?: boolean;
}

export interface IUserRepository {
  findByEmail(email: string): Promise<UserEntity | null>;
  findById(id: string): Promise<UserEntity | null>;
  create(data: CreateUserData): Promise<UserEntity>;
  update(id: string, data: UpdateUserData): Promise<UserEntity | null>;
  list(page: number, pageSize: number, filters?: UserListFilters): Promise<Paginated<UserEntity>>;
}
