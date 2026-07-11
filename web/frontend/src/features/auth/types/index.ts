import type { AuthResponse, AuthUser } from '@optiagent/shared';

export type { AuthResponse, AuthUser, LoginRequest, TokenPair } from '@optiagent/shared';

export interface AuthState {
  user: AuthUser | null;
  accessToken: string | null;
  refreshToken: string | null;
}

export type LoginSuccess = AuthResponse;
