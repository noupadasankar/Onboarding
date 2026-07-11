export type DocumentStatus = 'PENDING' | 'INDEXING' | 'INDEXED' | 'FAILED' | 'DELETED';

export interface DocumentDTO {
  id: string;
  filename: string;
  originalName: string;
  mimeType: string;
  sizeBytes: number;
  status: DocumentStatus;
  departmentId: string | null;
  department?: { name: string } | null;
  uploadedById: string;
  chunkCount: number | null;
  vectorCount: number | null;
  errorMessage: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface DocumentListParams {
  page?: number;
  pageSize?: number;
  departmentId?: string;
}

export interface DocumentPage {
  items: DocumentDTO[];
  total: number;
  page: number;
  pageSize: number;
}
