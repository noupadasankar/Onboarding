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
 * Wraps the base query with transparent refresh: on a 401, attempt one token
 * rotation via /auth/refresh and replay the original request. On failure, clear
 * the session (forcing re-login). A single-flight guard avoids refresh stampedes.
 */
let refreshInFlight: Promise<boolean> | null = null;

const baseQueryWithReauth: BaseQueryFn<
  string | FetchArgs,
  unknown,
  FetchBaseQueryError
> = async (args, api, extraOptions) => {
  let result = await rawBaseQuery(args, api, extraOptions);

  if (result.error?.status === 401) {
    const state = api.getState() as RootState;
    const refreshToken = state.auth.refreshToken;

    if (refreshToken) {
      refreshInFlight ??= (async () => {
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
