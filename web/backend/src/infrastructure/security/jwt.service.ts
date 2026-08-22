/**
 * RS256 JWT signing/verification for access + refresh tokens. Asymmetric keys let
 * downstream verifiers hold only the public key. Behind an interface for testability.
 */
import { inject, injectable } from 'inversify';
import jwt, { type SignOptions } from 'jsonwebtoken';
import { randomUUID } from 'node:crypto';
import type {
  AccessTokenClaims,
  RefreshTokenClaims,
  Role,
} from '@hr-onboarding/shared';
import { ErrorCode } from '@hr-onboarding/shared';
import { TYPES } from '../../core/di/types';
import type { AppConfig } from '../../config/env';
import { UnauthorizedError } from '../../core/errors/app-error';

export interface AccessTokenResult {
  token: string;
  expiresIn: number;
}

export interface RefreshTokenResult {
  token: string;
  jti: string;
  expiresAt: Date;
}

export interface IJwtService {
  signAccessToken(input: { userId: string; email: string; role: Role }): AccessTokenResult;
  signRefreshToken(userId: string): RefreshTokenResult;
  verifyAccessToken(token: string): AccessTokenClaims;
  verifyRefreshToken(token: string): RefreshTokenClaims;
}

@injectable()
export class JwtService implements IJwtService {
  constructor(@inject(TYPES.Config) private readonly config: AppConfig) {}

  private get baseSignOptions(): SignOptions {
    return {
      algorithm: 'RS256',
      issuer: this.config.jwt.issuer,
      audience: this.config.jwt.audience,
    };
  }

  signAccessToken(input: { userId: string; email: string; role: Role }): AccessTokenResult {
    const expiresIn = this.config.jwt.accessTtlSeconds;
    const payload: Omit<AccessTokenClaims, 'sub'> = {
      email: input.email,
      role: input.role,
      type: 'access',
    };
    const token = jwt.sign(payload, this.config.jwt.privateKey, {
      ...this.baseSignOptions,
      subject: input.userId,
      expiresIn,
    });
    return { token, expiresIn };
  }

  signRefreshToken(userId: string): RefreshTokenResult {
    const jti = randomUUID();
    const expiresIn = this.config.jwt.refreshTtlSeconds;
    const token = jwt.sign({ type: 'refresh', jti }, this.config.jwt.privateKey, {
      ...this.baseSignOptions,
      subject: userId,
      expiresIn,
    });
    const expiresAt = new Date(Date.now() + expiresIn * 1000);
    return { token, jti, expiresAt };
  }

  verifyAccessToken(token: string): AccessTokenClaims {
    const claims = this.verify(token);
    if (claims.type !== 'access') {
      throw new UnauthorizedError('Wrong token type', ErrorCode.TOKEN_INVALID);
    }
    return claims as AccessTokenClaims;
  }

  verifyRefreshToken(token: string): RefreshTokenClaims {
    const claims = this.verify(token);
    if (claims.type !== 'refresh') {
      throw new UnauthorizedError('Wrong token type', ErrorCode.TOKEN_INVALID);
    }
    return claims as RefreshTokenClaims;
  }

  private verify(token: string): { type?: string } & jwt.JwtPayload {
    try {
      return jwt.verify(token, this.config.jwt.publicKey, {
        algorithms: ['RS256'],
        issuer: this.config.jwt.issuer,
        audience: this.config.jwt.audience,
      }) as jwt.JwtPayload;
    } catch (error) {
      if (error instanceof jwt.TokenExpiredError) {
        throw new UnauthorizedError('Token expired', ErrorCode.TOKEN_EXPIRED);
      }
      throw new UnauthorizedError('Invalid token', ErrorCode.TOKEN_INVALID);
    }
  }
}
