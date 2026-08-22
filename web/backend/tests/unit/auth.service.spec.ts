import 'reflect-metadata';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { Role } from '@hr-onboarding/shared';
import { AuthService } from '../../src/modules/auth/application/auth.service';
import { UserEntity } from '../../src/modules/users/domain/user.entity';
import { AppError } from '../../src/core/errors/app-error';
import type { IUserRepository } from '../../src/modules/users/domain/user.repository';
import type { IJwtService } from '../../src/infrastructure/security/jwt.service';
import type { IPasswordService } from '../../src/infrastructure/security/password.service';
import type { ITokenStore } from '../../src/infrastructure/security/token-store';
import type { IAuditLogService } from '../../src/infrastructure/audit/audit-log.service';

/** Purely mocked collaborators — this proves the service depends only on interfaces. */
function makeUser(overrides: Partial<{ isActive: boolean }> = {}): UserEntity {
  return new UserEntity({
    id: 'u_1',
    email: 'hr.manager@optiagent.dev',
    passwordHash: 'hashed',
    department: 'HR',
    isActive: overrides.isActive ?? true,
    role: Role.HR_MANAGER,
    createdAt: new Date(),
  });
}

describe('AuthService', () => {
  let users: IUserRepository;
  let jwt: IJwtService;
  let passwords: IPasswordService;
  let tokenStore: ITokenStore;
  let audit: IAuditLogService;
  let service: AuthService;

  beforeEach(() => {
    users = {
      findByEmail: vi.fn(),
      findById: vi.fn(),
      create: vi.fn(),
      update: vi.fn(),
      list: vi.fn(),
    };
    jwt = {
      signAccessToken: vi.fn().mockReturnValue({ token: 'access', expiresIn: 900 }),
      signRefreshToken: vi
        .fn()
        .mockReturnValue({ token: 'refresh', jti: 'jti-1', expiresAt: new Date(Date.now() + 1000) }),
      verifyAccessToken: vi.fn(),
      verifyRefreshToken: vi.fn(),
    };
    passwords = { hash: vi.fn(), verify: vi.fn() };
    tokenStore = { store: vi.fn(), isActive: vi.fn(), revoke: vi.fn() };
    audit = { log: vi.fn().mockResolvedValue(undefined) };
    service = new AuthService(users, jwt, passwords, tokenStore, audit);
  });

  it('issues tokens on valid credentials and records the refresh jti', async () => {
    (users.findByEmail as any).mockResolvedValue(makeUser());
    (passwords.verify as any).mockResolvedValue(true);

    const result = await service.login('hr.manager@optiagent.dev', 'Password123!');

    expect(result.tokens.accessToken).toBe('access');
    expect(result.tokens.refreshToken).toBe('refresh');
    expect(result.user.role).toBe(Role.HR_MANAGER);
    expect(tokenStore.store).toHaveBeenCalledWith('jti-1', 'u_1', expect.any(Number));
  });

  it('rejects invalid credentials without revealing which factor failed', async () => {
    (users.findByEmail as any).mockResolvedValue(makeUser());
    (passwords.verify as any).mockResolvedValue(false);

    await expect(service.login('hr.manager@optiagent.dev', 'wrong')).rejects.toMatchObject({
      statusCode: 401,
    });
  });

  it('rejects disabled accounts', async () => {
    (users.findByEmail as any).mockResolvedValue(makeUser({ isActive: false }));
    (passwords.verify as any).mockResolvedValue(true);

    await expect(service.login('x', 'y')).rejects.toBeInstanceOf(AppError);
  });

  it('rotates the refresh token on refresh (revoke old, issue new)', async () => {
    (jwt.verifyRefreshToken as any).mockReturnValue({ sub: 'u_1', jti: 'old-jti', type: 'refresh' });
    (tokenStore.isActive as any).mockResolvedValue(true);
    (users.findById as any).mockResolvedValue(makeUser());

    await service.refresh('refresh-token');

    expect(tokenStore.revoke).toHaveBeenCalledWith('old-jti');
    expect(tokenStore.store).toHaveBeenCalledWith('jti-1', 'u_1', expect.any(Number));
  });

  it('rejects a refresh token that is no longer active', async () => {
    (jwt.verifyRefreshToken as any).mockReturnValue({ sub: 'u_1', jti: 'old', type: 'refresh' });
    (tokenStore.isActive as any).mockResolvedValue(false);

    await expect(service.refresh('refresh-token')).rejects.toMatchObject({ statusCode: 401 });
    expect(users.findById).not.toHaveBeenCalled();
  });

  it('revokes the refresh jti on logout', async () => {
    (jwt.verifyRefreshToken as any).mockReturnValue({ sub: 'u_1', jti: 'jti-x', type: 'refresh' });
    await service.logout('refresh-token');
    expect(tokenStore.revoke).toHaveBeenCalledWith('jti-x');
  });

  it('writes a LOGIN_SUCCESS audit entry on successful login', async () => {
    (users.findByEmail as any).mockResolvedValue(makeUser());
    (passwords.verify as any).mockResolvedValue(true);

    await service.login('hr.manager@optiagent.dev', 'Password123!');

    expect(audit.log).toHaveBeenCalledWith(
      expect.objectContaining({ action: 'LOGIN_SUCCESS', userId: 'u_1' }),
    );
  });

  it('does not write an audit entry on failed login', async () => {
    (users.findByEmail as any).mockResolvedValue(makeUser());
    (passwords.verify as any).mockResolvedValue(false);

    await expect(service.login('x', 'wrong')).rejects.toMatchObject({ statusCode: 401 });
    expect(audit.log).not.toHaveBeenCalled();
  });
});
