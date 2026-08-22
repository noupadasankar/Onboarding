import type { ApiResponse } from '@hr-onboarding/shared';
import { isApiFailure } from '@hr-onboarding/shared';
import { baseApi } from '@/app/api/baseApi';
import type { NotificationListResult } from '../types';

function unwrap<T>(res: ApiResponse<T>): T {
  if (isApiFailure(res)) throw new Error(res.error.message);
  return res.data;
}

interface ListNotificationsParams {
  page?: number;
  pageSize?: number;
  unreadOnly?: boolean;
}

export const notificationsApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    listNotifications: builder.query<NotificationListResult, ListNotificationsParams | void>({
      query: (params) => ({ url: '/notifications', params: params ?? {} }),
      transformResponse: (res: ApiResponse<NotificationListResult>) => unwrap(res),
      providesTags: (result) =>
        result
          ? [
              ...result.items.map(({ id }) => ({ type: 'Notification' as const, id })),
              { type: 'Notification', id: 'LIST' },
            ]
          : [{ type: 'Notification', id: 'LIST' }],
    }),
    markRead: builder.mutation<{ read: boolean }, string>({
      query: (id) => ({ url: `/notifications/${id}/read`, method: 'PATCH' }),
      transformResponse: (res: ApiResponse<{ read: boolean }>) => unwrap(res),
      invalidatesTags: (_result, _err, id) => [
        { type: 'Notification', id: 'LIST' },
        { type: 'Notification', id },
      ],
    }),
    markAllRead: builder.mutation<{ updated: number }, void>({
      query: () => ({ url: '/notifications/read-all', method: 'PATCH' }),
      transformResponse: (res: ApiResponse<{ updated: number }>) => unwrap(res),
      invalidatesTags: [{ type: 'Notification', id: 'LIST' }],
    }),
  }),
});

export const {
  useListNotificationsQuery,
  useMarkReadMutation,
  useMarkAllReadMutation,
} = notificationsApi;
