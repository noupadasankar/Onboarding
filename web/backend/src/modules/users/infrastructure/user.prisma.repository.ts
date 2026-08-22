/**
 * Prisma-backed implementation of IUserRepository. The ONLY place users touch the
 * database. Translates persistence rows ↔ the UserEntity domain object.
 */
import { inject, injectable } from 'inversify';
import { RoleName } from '@prisma/client';
import type { User as PrismaUser, Role as PrismaRole } from '@prisma/client';
import type { Paginated, Role } from '@hr-onboarding/shared';
import { TYPES } from '../../../core/di/types';
import type { PrismaService } from '../../../infrastructure/database/prisma.service';
import { UserEntity } from '../domain/user.entity';
import type {
  CreateUserData,
  IUserRepository,
  UpdateUserData,
  UserListFilters,
} from '../domain/user.repository';

type UserWithRole = PrismaUser & { role: PrismaRole };

@injectable()
export class UserPrismaRepository implements IUserRepository {
  constructor(@inject(TYPES.PrismaService) private readonly prisma: PrismaService) {}

  private get users() {
    return this.prisma.client.user;
  }

  async findByEmail(email: string): Promise<UserEntity | null> {
    const row = await this.users.findUnique({
      where: { email },
      include: { role: true },
    });
    return row ? this.toEntity(row) : null;
  }

  async findById(id: string): Promise<UserEntity | null> {
    const row = await this.users.findUnique({
      where: { id },
      include: { role: true },
    });
    return row ? this.toEntity(row) : null;
  }

  async create(data: CreateUserData): Promise<UserEntity> {
    const row = await this.users.create({
      data: {
        email: data.email,
        passwordHash: data.passwordHash,
        department: data.department ?? null,
        role: { connect: { name: data.role as unknown as RoleName } },
      },
      include: { role: true },
    });
    return this.toEntity(row);
  }

  async update(id: string, data: UpdateUserData): Promise<UserEntity | null> {
    try {
      const row = await this.users.update({
        where: { id },
        data: {
          ...(data.role !== undefined && {
            role: { connect: { name: data.role as unknown as RoleName } },
          }),
          ...(data.department !== undefined && { department: data.department }),
          ...(data.isActive !== undefined && { isActive: data.isActive }),
        },
        include: { role: true },
      });
      return this.toEntity(row);
    } catch {
      // Prisma throws P2025 when the record doesn't exist.
      return null;
    }
  }

  async list(
    page: number,
    pageSize: number,
    filters?: UserListFilters,
  ): Promise<Paginated<UserEntity>> {
    const where = this.buildWhere(filters);
    const skip = (page - 1) * pageSize;
    const [rows, total] = await Promise.all([
      this.users.findMany({
        skip,
        take: pageSize,
        where,
        orderBy: { createdAt: 'desc' },
        include: { role: true },
      }),
      this.users.count({ where }),
    ]);
    return { items: (rows as UserWithRole[]).map((r) => this.toEntity(r)), total, page, pageSize };
  }

  private buildWhere(filters?: UserListFilters) {
    if (!filters) return undefined;
    return {
      ...(filters.search && {
        email: { contains: filters.search, mode: 'insensitive' as const },
      }),
      ...(filters.role !== undefined && {
        role: { name: filters.role as unknown as RoleName },
      }),
      ...(filters.isActive !== undefined && { isActive: filters.isActive }),
    };
  }

  private toEntity(row: UserWithRole): UserEntity {
    return new UserEntity({
      id: row.id,
      email: row.email,
      passwordHash: row.passwordHash,
      department: row.department,
      isActive: row.isActive,
      role: row.role.name as unknown as Role,
      createdAt: row.createdAt,
    });
  }
}
