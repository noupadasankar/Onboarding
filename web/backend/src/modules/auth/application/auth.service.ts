/**
 * Authentication application service. Orchestrates the security primitives
 * (password verify, JWT sign, refresh-token store) over the user repository.
 * All collaborators are interfaces injected via DI — enabling isolated unit tests.
 */
import { inject, injectable } from 'inversify';
import type { AuthResponse, TokenPair } from '@optiagent/shared';
import { ErrorCode } from '@optiagent/shared';
import { TYPES } from '../../../core/di/types';
import { UnauthorizedError } from '../../../core/errors/app-error';
import type { IUserRepository } from '../../users/domain/user.repository';
import type { UserEntity } from '../../users/domain/user.entity';
import type { IJwtService } from '../../../infrastructure/security/jwt.service';
import type { IPasswordService } from '../../../infrastructure/security/password.service';
import type { ITokenStore } from '../../../infrastructure/security/token-store';
import type { IAuditLogService } from '../../../infrastructure/audit/audit-log.service';

export interface AuthRequestContext {
  ipAddress?: string;
  requestId?: string;
}

export interface IAuthService {
  login(
    email: string,
    password: string,
    ctx?: AuthRequestContext,
  ): Promise<AuthResponse>;
  refresh(refreshToken: string): Promise<AuthResponse>;
  logout(refreshToken: string, ctx?: AuthRequestContext): Promise<void>;
}

@injectable()
export class AuthService implements IAuthService {
  constructor(
    @inject(TYPES.UserRepository) private readonly users: IUserRepository,
    @inject(TYPES.JwtService) private readonly jwt: IJwtService,
    @inject(TYPES.PasswordService) private readonly passwords: IPasswordService,
    @inject(TYPES.TokenStore) private readonly tokenStore: ITokenStore,
    @inject(TYPES.AuditLogService) private readonly audit: IAuditLogService,
  ) {}

  async login(
    email: string,
    password: string,
    ctx?: AuthRequestContext,
  ): Promise<AuthResponse> {
    const user = await this.users.findByEmail(email);
    // Always run a comparison to avoid leaking which emails exist (timing).
    const hash = user?.passwordHash ?? '$2a$12$invalidinvalidinvalidinvalidinvalidinvalidinv';
    const valid = await this.passwords.verify(password, hash);

    if (!user || !valid) {
      throw new UnauthorizedError('Invalid email or password', ErrorCode.INVALID_CREDENTIALS);
    }
    if (!user.isActive) {
      throw new UnauthorizedError('Account is disabled', ErrorCode.ACCOUNT_DISABLED);
    }

    const response = await this.issue(user);

    await this.audit.log({
      userId: user.id,
      action: 'LOGIN_SUCCESS',
      resource: 'auth',
      ipAddress: ctx?.ipAddress,
      requestId: ctx?.requestId,
    });

    return response;
  }

  async refresh(refreshToken: string): Promise<AuthResponse> {
    const claims = this.jwt.verifyRefreshToken(refreshToken);

    // Reject rotated/revoked/unknown refresh tokens.
    if (!(await this.tokenStore.isActive(claims.jti))) {
      throw new UnauthorizedError('Refresh token is no longer valid', ErrorCode.TOKEN_INVALID);
    }
    // Rotate: the presented refresh token is single-use.
    await this.tokenStore.revoke(claims.jti);

    const user = await this.users.findById(claims.sub);
    if (!user || !user.isActive) {
      throw new UnauthorizedError('Account unavailable', ErrorCode.ACCOUNT_DISABLED);
    }
    return this.issue(user);
  }

  async logout(refreshToken: string, ctx?: AuthRequestContext): Promise<void> {
    try {
      const claims = this.jwt.verifyRefreshToken(refreshToken);
      await this.tokenStore.revoke(claims.jti);

      await this.audit.log({
        userId: claims.sub,
        action: 'LOGOUT',
        resource: 'auth',
        ipAddress: ctx?.ipAddress,
        requestId: ctx?.requestId,
      });
    } catch {
      // Logout is idempotent — an invalid/expired token is already "logged out".
    }
  }

  /** Sign a fresh access+refresh pair and record the refresh jti as active. */
  private async issue(user: UserEntity): Promise<AuthResponse> {
    const access = this.jwt.signAccessToken({
      userId: user.id,
      email: user.email,
      role: user.role,
    });
    const refresh = this.jwt.signRefreshToken(user.id);

    const ttlSeconds = Math.max(
      Math.floor((refresh.expiresAt.getTime() - Date.now()) / 1000),
      1,
    );
    await this.tokenStore.store(refresh.jti, user.id, ttlSeconds);

    const tokens: TokenPair = {
      accessToken: access.token,
      expiresIn: access.expiresIn,
      refreshToken: refresh.token,
    };
    return { user: user.toAuthUser(), tokens };
  }
}
