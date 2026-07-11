import type { ApiResponse, RoleDTO } from '@optiagent/shared';
import { isApiFailure } from '@optiagent/shared';
import { baseApi } from '@/app/api/baseApi';

function unwrap<T>(res: ApiResponse<T>): T {
  if (isApiFailure(res)) throw new Error(res.error.message);
  return res.data;
}

export const rolesApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    getRoles: builder.query<RoleDTO[], void>({
      query: () => '/roles',
      transformResponse: (res: ApiResponse<RoleDTO[]>) => unwrap(res),
      providesTags: ['Role'],
    }),
    getPermissions: builder.query<string[], void>({
      query: () => '/permissions',
      transformResponse: (res: ApiResponse<string[]>) => unwrap(res),
    }),
  }),
});

export const { useGetRolesQuery, useGetPermissionsQuery } = rolesApi;
