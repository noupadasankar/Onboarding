/**
 * User application service. Business operations over users, expressed in domain
 * terms and returning client-safe projections. All collaborators are injected
 * interfaces, keeping this service trivially unit-testable.
 */
import { inject, injectable } from 'inversify';
import type { AuthUser, CreateUserRequest, Paginated, UpdateUserRequest } from '@optiagent/shared';
import { TYPES } from '../../../core/di/types';
import { ConflictError, NotFoundError } from '../../../core/errors/app-error';
import type { IAuditLogService } from '../../../infrastructure/audit/audit-log.service';
import type { IPasswordService } from '../../../infrastructure/security/password.service';
import type { IUserRepository, UserListFilters } from '../domain/user.repository';
import type { UserDTO } from '@optiagent/shared';

export interface IUserService {
  list(page: number, pageSize: number, filters?: UserListFilters): Promise<Paginated<UserDTO>>;
  getById(id: string): Promise<UserDTO>;
  me(id: string): Promise<AuthUser>;
  create(dto: CreateUserRequest, requestContext?: RequestContext): Promise<UserDTO>;
  update(id: string, dto: UpdateUserRequest, requestContext?: RequestContext): Promise<UserDTO>;
  deactivate(id: string, requestContext?: RequestContext): Promise<void>;
}

export interface RequestContext {
  actorId?: string;
  ipAddress?: string;
  requestId?: string;
}

@injectable()
export class UserService implements IUserService {
  constructor(
    @inject(TYPES.UserRepository) private readonly users: IUserRepository,
    @inject(TYPES.PasswordService) private readonly passwords: IPasswordService,
    @inject(TYPES.AuditLogService) private readonly audit: IAuditLogService,
  ) {}

  async list(
    page: number,
    pageSize: number,
    filters?: UserListFilters,
  ): Promise<Paginated<UserDTO>> {
    const result = await this.users.list(page, pageSize, filters);
    return { ...result, items: result.items.map((u) => u.toUserDTO()) };
  }

  async getById(id: string): Promise<UserDTO> {
    const user = await this.users.findById(id);
    if (!user) throw new NotFoundError('User not found');
    return user.toUserDTO();
  }

  async me(id: string): Promise<AuthUser> {
    const user = await this.users.findById(id);
    if (!user) throw new NotFoundError('User not found');
    return user.toAuthUser();
  }

  async create(dto: CreateUserRequest, ctx?: RequestContext): Promise<UserDTO> {
    const existing = await this.users.findByEmail(dto.email);
    if (existing) throw new ConflictError('Email address is already in use');

    const passwordHash = await this.passwords.hash(dto.password);
    const user = await this.users.create({
      email: dto.email,
      passwordHash,
      role: dto.role,
      department: dto.department ?? null,
    });

    await this.audit.log({
      userId: ctx?.actorId,
      action: 'USER_CREATED',
      resource: `users/${user.id}`,
      metadata: { email: user.email, role: user.role },
      ipAddress: ctx?.ipAddress,
      requestId: ctx?.requestId,
    });

    return user.toUserDTO();
  }

  async update(id: string, dto: UpdateUserRequest, ctx?: RequestContext): Promise<UserDTO> {
    const user = await this.users.update(id, dto);
    if (!user) throw new NotFoundError('User not found');

    await this.audit.log({
      userId: ctx?.actorId,
      action: 'USER_UPDATED',
      resource: `users/${id}`,
      metadata: { changes: dto },
      ipAddress: ctx?.ipAddress,
      requestId: ctx?.requestId,
    });

    return user.toUserDTO();
  }

  async deactivate(id: string, ctx?: RequestContext): Promise<void> {
    const user = await this.users.update(id, { isActive: false });
    if (!user) throw new NotFoundError('User not found');

    await this.audit.log({
      userId: ctx?.actorId,
      action: 'USER_DEACTIVATED',
      resource: `users/${id}`,
      ipAddress: ctx?.ipAddress,
      requestId: ctx?.requestId,
    });
  }
}
