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
    getDocumentVersions: builder.query<DocumentPage['items'], string>({
      query: (id) => `/documents/${id}/versions`,
      transformResponse: (res: ApiResponse<{ items: DocumentDTO[] }>) => unwrap(res).items,
      providesTags: (_result, _err, id) => [{ type: 'Document', id: `${id}:versions` }],
    }),
    // Download returns raw file bytes (not the JSON envelope), so bypass unwrap
    // and read the response as a Blob for the browser to save.
    downloadDocument: builder.mutation<Blob, string>({
      query: (id) => ({
        url: `/documents/${id}/download`,
        responseHandler: (response) => response.blob(),
      }),
    }),
  }),
});

export const {
  useListDocumentsQuery,
  useGetDocumentQuery,
  useUploadDocumentMutation,
  useDeleteDocumentMutation,
  useGetDocumentVersionsQuery,
  useDownloadDocumentMutation,
} = documentsApi;
