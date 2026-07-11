import type { ApiResponse } from '@optiagent/shared';
import { isApiFailure } from '@optiagent/shared';
import { baseApi } from '@/app/api/baseApi';
import type { DocumentDTO, DocumentListParams, DocumentPage } from '../types';

function unwrap<T>(res: ApiResponse<T>): T {
  if (isApiFailure(res)) throw new Error(res.error.message);
  return res.data;
}

export const documentsApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    listDocuments: builder.query<DocumentPage, DocumentListParams | void>({
      query: (params) => ({ url: '/documents', params: params ?? {} }),
      transformResponse: (res: ApiResponse<DocumentPage>) => unwrap(res),
      providesTags: (result) =>
        result
          ? [
              ...result.items.map(({ id }) => ({ type: 'Document' as const, id })),
              { type: 'Document', id: 'LIST' },
            ]
          : [{ type: 'Document', id: 'LIST' }],
    }),
    getDocument: builder.query<DocumentDTO, string>({
      query: (id) => `/documents/${id}`,
      transformResponse: (res: ApiResponse<DocumentDTO>) => unwrap(res),
      providesTags: (_result, _err, id) => [{ type: 'Document', id }],
    }),
    uploadDocument: builder.mutation<DocumentDTO, FormData>({
      query: (body) => ({ url: '/documents/upload', method: 'POST', body, formData: true }),
      transformResponse: (res: ApiResponse<DocumentDTO>) => unwrap(res),
      invalidatesTags: [{ type: 'Document', id: 'LIST' }],
    }),
    deleteDocument: builder.mutation<{ deleted: boolean }, string>({
      query: (id) => ({ url: `/documents/${id}`, method: 'DELETE' }),
      transformResponse: (res: ApiResponse<{ deleted: boolean }>) => unwrap(res),
      invalidatesTags: (_result, _err, id) => [
        { type: 'Document', id: 'LIST' },
        { type: 'Document', id },
      ],
    }),
  }),
});

export const {
  useListDocumentsQuery,
  useGetDocumentQuery,
  useUploadDocumentMutation,
  useDeleteDocumentMutation,
} = documentsApi;
