import type { AuthResponse, AuthUser } from '@hr-onboarding/shared';

export type { AuthResponse, AuthUser, LoginRequest, TokenPair } from '@hr-onboarding/shared';

export interface AuthState {
  user: AuthUser | null;
  accessToken: string | null;
  refreshToken: string | null;
}

export type LoginSuccess = AuthResponse;
