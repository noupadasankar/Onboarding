import type { ApiResponse } from '@hr-onboarding/shared';
import { isApiFailure } from '@hr-onboarding/shared';
import { baseApi } from '@/app/api/baseApi';
import type { AdminSettingDTO } from '../types';

function unwrap<T>(res: ApiResponse<T>): T {
  if (isApiFailure(res)) throw new Error(res.error.message);
  return res.data;
}

export const adminSettingsApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    listSettings: builder.query<AdminSettingDTO[], void>({
      query: () => '/admin/settings',
      transformResponse: (res: ApiResponse<AdminSettingDTO[]>) => unwrap(res),
      providesTags: (result) =>
        result
          ? [
              ...result.map((s) => ({ type: 'AdminSetting' as const, id: s.key })),
              { type: 'AdminSetting', id: 'LIST' },
            ]
          : [{ type: 'AdminSetting', id: 'LIST' }],
    }),
    getSetting: builder.query<AdminSettingDTO, string>({
      query: (key) => `/admin/settings/${key}`,
      transformResponse: (res: ApiResponse<AdminSettingDTO>) => unwrap(res),
      providesTags: (_result, _err, key) => [{ type: 'AdminSetting', id: key }],
    }),
    upsertSetting: builder.mutation<
      AdminSettingDTO,
      { key: string; value: unknown; description?: string }
    >({
      query: ({ key, value, description }) => ({
        url: `/admin/settings/${key}`,
        method: 'PUT',
        body: { value, description },
      }),
      transformResponse: (res: ApiResponse<AdminSettingDTO>) => unwrap(res),
      invalidatesTags: (_result, _err, { key }) => [
        { type: 'AdminSetting', id: 'LIST' },
        { type: 'AdminSetting', id: key },
      ],
    }),
    deleteSetting: builder.mutation<{ deleted: boolean }, string>({
      query: (key) => ({ url: `/admin/settings/${key}`, method: 'DELETE' }),
      transformResponse: (res: ApiResponse<{ deleted: boolean }>) => unwrap(res),
      invalidatesTags: (_result, _err, key) => [
        { type: 'AdminSetting', id: 'LIST' },
        { type: 'AdminSetting', id: key },
      ],
    }),
  }),
});

export const {
  useListSettingsQuery,
  useGetSettingQuery,
  useUpsertSettingMutation,
  useDeleteSettingMutation,
} = adminSettingsApi;
