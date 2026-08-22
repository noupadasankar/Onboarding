import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';
import type {
  BaseQueryFn,
  FetchArgs,
  FetchBaseQueryError,
} from '@reduxjs/toolkit/query';
import type { ApiResponse, AuthResponse } from '@optiagent/shared';
import type { RootState } from '../store';
import { clearCredentials, setCredentials } from '@/features/auth/redux/authSlice';

const rawBaseQuery = fetchBaseQuery({
  baseUrl: import.meta.env.VITE_API_URL || '/api/v1',
  prepareHeaders: (headers, { getState }) => {
    const token = (getState() as RootState).auth.accessToken;
    if (token) headers.set('authorization', `Bearer ${token}`);
    return headers;
  },
});

/**
 * Decode JWT payload to check expiry without verification.
 * Returns exp timestamp in milliseconds, or null if invalid.
 */
function getTokenExpiry(token: string): number | null {
  try {
    const parts = token.split('.');
    const payload = parts[1];
    if (!payload) return null;
    const decoded = JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/')));
    return decoded.exp * 1000; // Convert to ms
  } catch {
    return null;
  }
}

/**
 * Check if access token is expiring soon (within threshold).
 */
function isTokenExpiringSoon(token: string, thresholdMs = 60_000): boolean {
  const exp = getTokenExpiry(token);
  if (!exp) return true;
  return Date.now() + thresholdMs >= exp;
}

/**
 * Wraps the base query with:
 * 1. Proactive token refresh before expiry
 * 2. Transparent refresh on 401 response
 * 3. Single-flight guard to avoid refresh stampedes
 */
let refreshInFlight: Promise<boolean> | null = null;

const baseQueryWithReauth: BaseQueryFn<
  string | FetchArgs,
  unknown,
  FetchBaseQueryError
> = async (args, api, extraOptions) => {
  const state = api.getState() as RootState;
  const accessToken = state.auth.accessToken;
  const refreshToken = state.auth.refreshToken;

  // Proactive refresh: if token expires within 60s, refresh before the request
  if (accessToken && refreshToken && isTokenExpiringSoon(accessToken)) {
    if (!refreshInFlight) {
      refreshInFlight = (async () => {
        const refreshResult = await rawBaseQuery(
          { url: '/auth/refresh', method: 'POST', body: { refreshToken } },
          api,
          extraOptions,
        );
        const body = refreshResult.data as ApiResponse<AuthResponse> | undefined;
        if (body?.success) {
          api.dispatch(setCredentials(body.data));
          return true;
        }
        api.dispatch(clearCredentials());
        return false;
      })();
    }

    const refreshed = await refreshInFlight;
    refreshInFlight = null;

    if (!refreshed) {
      return { error: { status: 401, data: { status: 401, name: 'Unauthorized', message: 'Token refresh failed' } } as unknown as FetchBaseQueryError };
    }
  }

  let result = await rawBaseQuery(args, api, extraOptions);

  // Reactive refresh on 401
  if (result.error?.status === 401) {
    const currentState = api.getState() as RootState;
    const currentRefreshToken = currentState.auth.refreshToken;

    if (currentRefreshToken) {
      if (!refreshInFlight) {
        refreshInFlight = (async () => {
          const refreshResult = await rawBaseQuery(
            { url: '/auth/refresh', method: 'POST', body: { refreshToken: currentRefreshToken } },
            api,
            extraOptions,
          );
          const body = refreshResult.data as ApiResponse<AuthResponse> | undefined;
          if (body?.success) {
            api.dispatch(setCredentials(body.data));
            return true;
          }
          api.dispatch(clearCredentials());
          return false;
        })();
      }

      const refreshed = await refreshInFlight;
      refreshInFlight = null;

      if (refreshed) {
        result = await rawBaseQuery(args, api, extraOptions);
      }
    } else {
      api.dispatch(clearCredentials());
    }
  }

  return result;
};

export const baseApi = createApi({
  reducerPath: 'api',
  baseQuery: baseQueryWithReauth,
  tagTypes: ['User', 'Role', 'Analytics', 'Notification', 'Conversation', 'Department', 'AdminSetting', 'Document'],
  endpoints: () => ({}),
});
