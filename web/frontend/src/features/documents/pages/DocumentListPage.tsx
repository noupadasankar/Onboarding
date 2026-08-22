import { useMemo, useState } from 'react';
import { Permission } from '@hr-onboarding/shared';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/features/auth/hooks/useAuth';
// TODO: replace with useListDepartmentsQuery once departments feature is wired into this page
import { useListDepartmentsQuery } from '@/features/departments/api/departmentsApi';
import {
  useListDocumentsQuery,
  useDeleteDocumentMutation,
  useDownloadDocumentMutation,
} from '../api/documentsApi';
import { DocumentStatusBadge } from '../components/DocumentStatusBadge';
import { UploadDocumentModal } from '../components/UploadDocumentModal';
import { VersionHistoryModal } from '../components/VersionHistoryModal';
import {
  DocumentFilterBar,
  EMPTY_FILTERS,
  filtersToParams,
  type DocumentFilters,
} from '../components/DocumentFilterBar';

function formatSize(bytes: number): string {
  const mb = bytes / 1024 / 1024;
  if (mb >= 1) return `${mb.toFixed(1)} MB`;
  return `${Math.round(bytes / 1024)} KB`;
}

export function DocumentListPage() {
  const { hasPermission } = useAuth();
  const [page, setPage] = useState(1);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [filters, setFilters] = useState<DocumentFilters>(EMPTY_FILTERS);
  const [versionsFor, setVersionsFor] = useState<string | null>(null);

  const queryParams = useMemo(
    () => ({ page, pageSize: 20, ...filtersToParams(filters) }),
    [page, filters],
  );

  const { data, isLoading, isError } = useListDocumentsQuery(queryParams);
  const [deleteDocument] = useDeleteDocumentMutation();
  const [downloadDocument] = useDownloadDocumentMutation();

  // TODO: pass departments to UploadDocumentModal — using useListDepartmentsQuery
  const { data: departments = [] } = useListDepartmentsQuery();

  const totalPages = data ? Math.ceil(data.total / data.pageSize) : 0;

  const applyFilters = (next: DocumentFilters) => {
    setFilters(next);
    setPage(1); // filtering resets to the first page
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm('Are you sure you want to delete this document?')) return;
    try {
      await deleteDocument(id).unwrap();
    } catch {
      // Error is silently ignored; the cache will not update on failure
    }
  };

  const handleDownload = async (id: string, filename: string) => {
    try {
      const blob = await downloadDocument(id).unwrap();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch {
      // Download failed — leave the UI unchanged.
    }
  };

  return (
    <div className="p-6" data-testid="documents-page">
      <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Documents</h1>
          <p className="text-sm text-slate-500">Manage uploaded documents and their indexing status.</p>
        </div>
        {hasPermission(Permission.DOCUMENTS_UPLOAD) && (
          <Button onClick={() => setUploadOpen(true)} data-testid="upload-document-button">Upload document</Button>
        )}
      </div>

      <DocumentFilterBar
        value={filters}
        onChange={applyFilters}
        onReset={() => applyFilters(EMPTY_FILTERS)}
      />

      {isLoading && (
        <p className="py-8 text-center text-sm text-slate-500">Loading documents…</p>
      )}

      {isError && (
        <p className="py-8 text-center text-sm text-red-600">
          Failed to load documents. Please try again.
        </p>
      )}

      {data && (
        <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Name</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Department</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Size</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Status</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Uploaded</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100" data-testid="document-list">
              {data.items.map((doc) => (
                <tr key={doc.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3 font-medium text-slate-900">{doc.originalName}</td>
                  <td className="px-4 py-3 text-slate-600">
                    {doc.department?.name ?? '—'}
                  </td>
                  <td className="px-4 py-3 text-slate-600">{formatSize(doc.sizeBytes)}</td>
                  <td className="px-4 py-3">
                    <DocumentStatusBadge status={doc.status} />
                  </td>
                  <td className="px-4 py-3 text-slate-600">
                    {new Date(doc.createdAt).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex justify-end gap-1">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setVersionsFor(doc.id)}
                      >
                        Versions
                      </Button>
                      {hasPermission(Permission.DOCUMENTS_VIEW) && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDownload(doc.id, doc.originalName)}
                        >
                          Download
                        </Button>
                      )}
                      {doc.status !== 'DELETED' && hasPermission(Permission.DOCUMENTS_MANAGE) && (
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-red-600 hover:bg-red-50 hover:text-red-700"
                          onClick={() => handleDelete(doc.id)}
                        >
                          Delete
                        </Button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
              {data.items.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-slate-500">
                    No documents found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>

          {totalPages > 1 && (
            <div className="flex items-center justify-between border-t border-slate-200 px-4 py-3">
              <span className="text-xs text-slate-500">
                Page {data.page} of {totalPages} · {data.total} total
              </span>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={data.page <= 1}
                  onClick={() => setPage(data.page - 1)}
                >
                  Prev
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={data.page >= totalPages}
                  onClick={() => setPage(data.page + 1)}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </div>
      )}

      <UploadDocumentModal
        open={uploadOpen}
        onClose={() => setUploadOpen(false)}
        departments={departments}
      />

      <VersionHistoryModal
        documentId={versionsFor}
        onClose={() => setVersionsFor(null)}
      />
    </div>
  );
}
