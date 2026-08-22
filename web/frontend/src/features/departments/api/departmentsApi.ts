import type { ApiResponse } from '@hr-onboarding/shared';
import { isApiFailure } from '@hr-onboarding/shared';
import { baseApi } from '@/app/api/baseApi';
import type { DepartmentDTO, CreateDepartmentRequest, UpdateDepartmentRequest } from '../types';

function unwrap<T>(res: ApiResponse<T>): T {
  if (isApiFailure(res)) throw new Error(res.error.message);
  return res.data;
}

export const departmentsApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    listDepartments: builder.query<DepartmentDTO[], { includeInactive?: boolean } | void>({
      query: (params) => ({ url: '/departments', params: params ?? {} }),
      transformResponse: (res: ApiResponse<DepartmentDTO[]>) => unwrap(res),
      providesTags: (result) =>
        result
          ? [
              ...result.map(({ id }) => ({ type: 'Department' as const, id })),
              { type: 'Department', id: 'LIST' },
            ]
          : [{ type: 'Department', id: 'LIST' }],
    }),
    getDepartment: builder.query<DepartmentDTO, string>({
      query: (id) => `/departments/${id}`,
      transformResponse: (res: ApiResponse<DepartmentDTO>) => unwrap(res),
      providesTags: (_result, _err, id) => [{ type: 'Department', id }],
    }),
    createDepartment: builder.mutation<DepartmentDTO, CreateDepartmentRequest>({
      query: (body) => ({ url: '/departments', method: 'POST', body }),
      transformResponse: (res: ApiResponse<DepartmentDTO>) => unwrap(res),
      invalidatesTags: [{ type: 'Department', id: 'LIST' }],
    }),
    updateDepartment: builder.mutation<DepartmentDTO, { id: string; body: UpdateDepartmentRequest }>({
      query: ({ id, body }) => ({ url: `/departments/${id}`, method: 'PATCH', body }),
      transformResponse: (res: ApiResponse<DepartmentDTO>) => unwrap(res),
      invalidatesTags: (_result, _err, { id }) => [
        { type: 'Department', id },
        { type: 'Department', id: 'LIST' },
      ],
    }),
  }),
});

export const {
  useListDepartmentsQuery,
  useGetDepartmentQuery,
  useCreateDepartmentMutation,
  useUpdateDepartmentMutation,
} = departmentsApi;
