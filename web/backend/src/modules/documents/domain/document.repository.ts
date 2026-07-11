/**
 * Document domain types and repository interface.
 */
export type DocumentStatus = 'PENDING' | 'INDEXING' | 'INDEXED' | 'FAILED' | 'SUPERSEDED' | 'DELETED';

export interface DocumentDTO {
  id: string;
  filename: string;
  originalName: string;
  mimeType: string;
  sizeBytes: number;
  storagePath: string;
  status: DocumentStatus;
  departmentId: string | null;
  departmentName: string | null;
  uploadedById: string;
  chunkCount: number | null;
  vectorCount: number | null;
  aiDocumentId: string | null;
  errorMessage: string | null;
  version: number;
  isLatest: boolean;
  parentDocumentId: string | null;
  supersededAt: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface CreateDocumentInput {
  filename: string;
  originalName: string;
  mimeType: string;
  sizeBytes: number;
  storagePath: string;
  departmentId?: string | null;
  uploadedById: string;
  version?: number;
  isLatest?: boolean;
  parentDocumentId?: string | null;
}

export interface UpdateDocumentStatusInput {
  status: DocumentStatus;
  chunkCount?: number | null;
  vectorCount?: number | null;
  aiDocumentId?: string | null;
  errorMessage?: string | null;
}

export interface DocumentListFilters {
  departmentId?: string;
  status?: DocumentStatus;
  uploadedById?: string;
}

export interface IDocumentRepository {
  findAll(page: number, pageSize: number, filters?: DocumentListFilters): Promise<{
    items: DocumentDTO[];
    total: number;
    page: number;
    pageSize: number;
  }>;
  findById(id: string): Promise<DocumentDTO | null>;
  create(input: CreateDocumentInput): Promise<DocumentDTO>;
  updateStatus(id: string, input: UpdateDocumentStatusInput): Promise<DocumentDTO | null>;
  softDelete(id: string): Promise<void>;
  /** Find the current latest (non-superseded) version by name + department. */
  findLatestByNameAndDept(originalName: string, departmentId: string | null): Promise<DocumentDTO | null>;
  /** Mark a document as superseded: sets isLatest=false, status=SUPERSEDED, supersededAt=now. */
  markSuperseded(id: string): Promise<DocumentDTO | null>;
}
