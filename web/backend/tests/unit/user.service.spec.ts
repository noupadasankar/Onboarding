import 'reflect-metadata';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { Role } from '@optiagent/shared';
import { UserService } from '../../src/modules/users/application/user.service';
import { UserEntity } from '../../src/modules/users/domain/user.entity';
import type { IUserRepository } from '../../src/modules/users/domain/user.repository';
import type { IPasswordService } from '../../src/infrastructure/security/password.service';
import type { IAuditLogService } from '../../src/infrastructure/audit/audit-log.service';

function makeUser(overrides: Partial<{ id: string; email: string; isActive: boolean }> = {}): UserEntity {
  return new UserEntity({
    id: overrides.id ?? 'u_1',
    email: overrides.email ?? 'it.admin@optiagent.dev',
    passwordHash: 'hashed',
    department: 'IT',
    isActive: overrides.isActive ?? true,
    role: Role.IT_ADMIN,
    createdAt: new Date('2024-01-01'),
  });
}

describe('UserService', () => {
  let users: IUserRepository;
  let passwords: IPasswordService;
  let audit: IAuditLogService;
  let service: UserService;

  beforeEach(() => {
    users = {
      findByEmail: vi.fn(),
      findById: vi.fn(),
      create: vi.fn(),
      update: vi.fn(),
      list: vi.fn(),
    };
    passwords = { hash: vi.fn(), verify: vi.fn() };
    audit = { log: vi.fn().mockResolvedValue(undefined) };
    service = new UserService(users, passwords, audit);
  });

  // --- list ---
  describe('list', () => {
    it('returns paginated user DTOs and forwards filters to repository', async () => {
      const entities = [makeUser()];
      (users.list as any).mockResolvedValue({ items: entities, total: 1, page: 1, pageSize: 20 });

      const result = await service.list(1, 20, { role: Role.IT_ADMIN });

      expect(users.list).toHaveBeenCalledWith(1, 20, { role: Role.IT_ADMIN });
      const first = result.items[0]!;
      expect(first.email).toBe('it.admin@optiagent.dev');
      expect(first).not.toHaveProperty('passwordHash');
    });
  });

  // --- getById ---
  describe('getById', () => {
    it('returns a UserDTO for an existing user', async () => {
      (users.findById as any).mockResolvedValue(makeUser());

      const dto = await service.getById('u_1');

      expect(dto.id).toBe('u_1');
      expect(dto.isActive).toBe(true);
    });

    it('throws NotFoundError when user does not exist', async () => {
      (users.findById as any).mockResolvedValue(null);

      await expect(service.getById('missing')).rejects.toMatchObject({ statusCode: 404 });
    });
  });

  // --- create ---
  describe('create', () => {
    it('hashes the password and creates the user', async () => {
      (users.findByEmail as any).mockResolvedValue(null);
      (passwords.hash as any).mockResolvedValue('$2a$hash');
      (users.create as any).mockResolvedValue(makeUser({ email: 'new@test.dev' }));

      const dto = await service.create(
        { email: 'new@test.dev', password: 'Password1!', role: Role.EMPLOYEE },
      );

      expect(passwords.hash).toHaveBeenCalledWith('Password1!');
      expect(users.create).toHaveBeenCalledWith(
        expect.objectContaining({ passwordHash: '$2a$hash', email: 'new@test.dev' }),
      );
      expect(dto.email).toBe('new@test.dev');
    });

    it('throws ConflictError when email is already in use', async () => {
      (users.findByEmail as any).mockResolvedValue(makeUser());

      await expect(
        service.create({ email: 'it.admin@optiagent.dev', password: 'Password1!', role: Role.EMPLOYEE }),
      ).rejects.toMatchObject({ statusCode: 409 });

      expect(users.create).not.toHaveBeenCalled();
    });

    it('writes a USER_CREATED audit entry', async () => {
      (users.findByEmail as any).mockResolvedValue(null);
      (passwords.hash as any).mockResolvedValue('hashed');
      (users.create as any).mockResolvedValue(makeUser());

      await service.create(
        { email: 'new@test.dev', password: 'Password1!', role: Role.EMPLOYEE },
        { actorId: 'u_admin', requestId: 'req-1' },
      );

      expect(audit.log).toHaveBeenCalledWith(
        expect.objectContaining({ action: 'USER_CREATED', userId: 'u_admin' }),
      );
    });
  });

  // --- update ---
  describe('update', () => {
    it('returns updated UserDTO on success', async () => {
      const updated = makeUser({ id: 'u_1' });
      (users.update as any).mockResolvedValue(updated);

      const dto = await service.update('u_1', { department: 'Finance' });

      expect(dto.id).toBe('u_1');
    });

    it('throws NotFoundError when user does not exist', async () => {
      (users.update as any).mockResolvedValue(null);

      await expect(service.update('missing', { isActive: false })).rejects.toMatchObject({
        statusCode: 404,
      });
    });

    it('writes a USER_UPDATED audit entry', async () => {
      (users.update as any).mockResolvedValue(makeUser());

      await service.update('u_1', { department: 'Finance' }, { actorId: 'u_admin' });

      expect(audit.log).toHaveBeenCalledWith(
        expect.objectContaining({ action: 'USER_UPDATED', userId: 'u_admin' }),
      );
    });
  });

  // --- deactivate ---
  describe('deactivate', () => {
    it('calls update with isActive false', async () => {
      (users.update as any).mockResolvedValue(makeUser({ isActive: false }));

      await service.deactivate('u_1');

      expect(users.update).toHaveBeenCalledWith('u_1', { isActive: false });
    });

    it('throws NotFoundError when user does not exist', async () => {
      (users.update as any).mockResolvedValue(null);

      await expect(service.deactivate('missing')).rejects.toMatchObject({ statusCode: 404 });
    });

    it('writes a USER_DEACTIVATED audit entry', async () => {
      (users.update as any).mockResolvedValue(makeUser({ isActive: false }));

      await service.deactivate('u_1', { actorId: 'u_admin' });

      expect(audit.log).toHaveBeenCalledWith(
        expect.objectContaining({ action: 'USER_DEACTIVATED', userId: 'u_admin' }),
      );
    });
  });
});
