import type { ApiResponse } from '@hr-onboarding/shared';
import { isApiFailure } from '@hr-onboarding/shared';
import { baseApi } from '@/app/api/baseApi';
import type { AnalyticsData } from '../types';

function unwrap<T>(res: ApiResponse<T>): T {
  if (isApiFailure(res)) throw new Error(res.error.message);
  return res.data;
}

export const analyticsApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    getAnalytics: builder.query<AnalyticsData, void>({
      query: () => '/analytics',
      transformResponse: (res: ApiResponse<AnalyticsData>) => unwrap(res),
      providesTags: ['Analytics'],
    }),
  }),
});

export const { useGetAnalyticsQuery } = analyticsApi;
