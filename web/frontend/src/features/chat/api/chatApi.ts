import type { ApiResponse } from '@optiagent/shared';
import { isApiFailure } from '@optiagent/shared';
import { baseApi } from '@/app/api/baseApi';
import type {
  ChatRequest,
  ChatResponse,
  ConversationDetailDTO,
  ConversationListResult,
} from '../types';

function unwrap<T>(res: ApiResponse<T>): T {
  if (isApiFailure(res)) throw new Error(res.error.message);
  return res.data;
}

export const chatApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    listConversations: builder.query<
      ConversationListResult,
      { page?: number; pageSize?: number }
    >({
      query: (params) => ({ url: '/conversations', params }),
      transformResponse: (res: ApiResponse<ConversationListResult>) => unwrap(res),
      providesTags: (result) =>
        result
          ? [
              ...result.items.map(({ id }) => ({ type: 'Conversation' as const, id })),
              { type: 'Conversation', id: 'LIST' },
            ]
          : [{ type: 'Conversation', id: 'LIST' }],
    }),

    getConversation: builder.query<ConversationDetailDTO, string>({
      query: (id) => `/conversations/${id}`,
      transformResponse: (res: ApiResponse<ConversationDetailDTO>) => unwrap(res),
      providesTags: (_result, _err, id) => [{ type: 'Conversation', id }],
    }),

    chat: builder.mutation<ChatResponse, ChatRequest>({
      query: (body) => ({ url: '/conversations/chat', method: 'POST', body }),
      transformResponse: (res: ApiResponse<ChatResponse>) => unwrap(res),
      invalidatesTags: [{ type: 'Conversation', id: 'LIST' }],
    }),

    archiveConversation: builder.mutation<{ archived: boolean }, string>({
      query: (id) => ({ url: `/conversations/${id}`, method: 'DELETE' }),
      transformResponse: (res: ApiResponse<{ archived: boolean }>) => unwrap(res),
      invalidatesTags: (_result, _err, id) => [
        { type: 'Conversation', id: 'LIST' },
        { type: 'Conversation', id },
      ],
    }),
  }),
});

export const {
  useListConversationsQuery,
  useGetConversationQuery,
  useChatMutation,
  useArchiveConversationMutation,
} = chatApi;
