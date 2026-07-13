export type DocumentStatus =
  | 'PENDING'
  | 'INDEXING'
  | 'INDEXED'
  | 'FAILED'
  | 'SUPERSEDED'
  | 'DELETED';

export interface DocumentDTO {
  id: string;
  filename: string;
  originalName: string;
  mimeType: string;
  sizeBytes: number;
  status: DocumentStatus;
  departmentId: string | null;
  department?: { name: string } | null;
  departmentName?: string | null;
  uploadedById: string;
  chunkCount: number | null;
  vectorCount: number | null;
  errorMessage: string | null;
  version: number;
  isLatest: boolean;
  parentDocumentId: string | null;
  supersededAt: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface DocumentListParams {
  page?: number;
  pageSize?: number;
  // Department is NOT sent — the backend forces it from the caller's role.
  status?: DocumentStatus;
  filename?: string;
  mimeType?: string;
  dateFrom?: string;
  dateTo?: string;
  version?: number;
  sizeMin?: number;
  sizeMax?: number;
}

export interface DocumentPage {
  items: DocumentDTO[];
  total: number;
  page: number;
  pageSize: number;
}
