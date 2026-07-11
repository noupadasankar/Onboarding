import type { ApiResponse, AuthResponse, AuthUser, LoginRequest } from '@optiagent/shared';
import { isApiFailure } from '@optiagent/shared';
import { baseApi } from '@/app/api/baseApi';

/** Unwrap the shared `{ success, data }` envelope to the payload RTK Query caches. */
function unwrap<T>(res: ApiResponse<T>): T {
  if (isApiFailure(res)) throw new Error(res.error.message);
  return res.data;
}

export const authApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    login: builder.mutation<AuthResponse, LoginRequest>({
      query: (body) => ({ url: '/auth/login', method: 'POST', body }),
      transformResponse: (res: ApiResponse<AuthResponse>) => unwrap(res),
    }),
    logout: builder.mutation<{ loggedOut: boolean }, { refreshToken: string }>({
      query: (body) => ({ url: '/auth/logout', method: 'POST', body }),
      transformResponse: (res: ApiResponse<{ loggedOut: boolean }>) => unwrap(res),
    }),
    me: builder.query<AuthUser, void>({
      query: () => ({ url: '/auth/me' }),
      transformResponse: (res: ApiResponse<AuthUser>) => unwrap(res),
      providesTags: ['User'],
    }),
  }),
});

export const { useLoginMutation, useLogoutMutation, useMeQuery } = authApi;
