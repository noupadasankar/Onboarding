import type {
  ApiResponse,
  CreateUserRequest,
  Paginated,
  UpdateUserRequest,
  UserDTO,
  UserListQuery,
} from '@hr-onboarding/shared';
import { isApiFailure } from '@hr-onboarding/shared';
import { baseApi } from '@/app/api/baseApi';

function unwrap<T>(res: ApiResponse<T>): T {
  if (isApiFailure(res)) throw new Error(res.error.message);
  return res.data;
}

export const usersApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    listUsers: builder.query<Paginated<UserDTO>, Partial<UserListQuery>>({
      query: (params) => ({ url: '/users', params }),
      transformResponse: (res: ApiResponse<Paginated<UserDTO>>) => unwrap(res),
      providesTags: (result) =>
        result
          ? [
              ...result.items.map(({ id }) => ({ type: 'User' as const, id })),
              { type: 'User', id: 'LIST' },
            ]
          : [{ type: 'User', id: 'LIST' }],
    }),
    getUserById: builder.query<UserDTO, string>({
      query: (id) => `/users/${id}`,
      transformResponse: (res: ApiResponse<UserDTO>) => unwrap(res),
      providesTags: (_result, _err, id) => [{ type: 'User', id }],
    }),
    createUser: builder.mutation<UserDTO, CreateUserRequest>({
      query: (body) => ({ url: '/users', method: 'POST', body }),
      transformResponse: (res: ApiResponse<UserDTO>) => unwrap(res),
      invalidatesTags: [{ type: 'User', id: 'LIST' }],
    }),
    updateUser: builder.mutation<UserDTO, { id: string; body: UpdateUserRequest }>({
      query: ({ id, body }) => ({ url: `/users/${id}`, method: 'PATCH', body }),
      transformResponse: (res: ApiResponse<UserDTO>) => unwrap(res),
      invalidatesTags: (_result, _err, { id }) => [
        { type: 'User', id },
        { type: 'User', id: 'LIST' },
      ],
    }),
    deactivateUser: builder.mutation<{ deactivated: boolean }, string>({
      query: (id) => ({ url: `/users/${id}`, method: 'DELETE' }),
      transformResponse: (res: ApiResponse<{ deactivated: boolean }>) => unwrap(res),
      invalidatesTags: (_result, _err, id) => [
        { type: 'User', id },
        { type: 'User', id: 'LIST' },
      ],
    }),
  }),
});

export const {
  useListUsersQuery,
  useGetUserByIdQuery,
  useCreateUserMutation,
  useUpdateUserMutation,
  useDeactivateUserMutation,
} = usersApi;
