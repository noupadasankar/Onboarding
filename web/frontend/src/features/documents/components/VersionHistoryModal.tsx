import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { DocumentStatusBadge } from './DocumentStatusBadge';
import { useGetDocumentVersionsQuery } from '../api/documentsApi';

interface Props {
  documentId: string | null;
  onClose: () => void;
}

/** Shows the full version chain (newest first) for a document. */
export function VersionHistoryModal({ documentId, onClose }: Props) {
  const open = documentId !== null;
  const { data: versions, isLoading, isError } = useGetDocumentVersionsQuery(documentId as string, {
    skip: !open,
  });

  return (
    <Dialog open={open} onClose={onClose}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Version history</DialogTitle>
        </DialogHeader>

        {isLoading && <p className="py-6 text-center text-sm text-slate-500">Loading…</p>}
        {isError && (
          <p className="py-6 text-center text-sm text-red-600">Failed to load version history.</p>
        )}

        {versions && (
          <div className="overflow-hidden rounded-lg border border-slate-200">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-3 py-2 text-left font-medium text-slate-600">Version</th>
                  <th className="px-3 py-2 text-left font-medium text-slate-600">Status</th>
                  <th className="px-3 py-2 text-left font-medium text-slate-600">Uploaded</th>
                  <th className="px-3 py-2 text-left font-medium text-slate-600">Current</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {versions.map((v) => (
                  <tr key={v.id} className="hover:bg-slate-50">
                    <td className="px-3 py-2 font-medium text-slate-900">v{v.version}</td>
                    <td className="px-3 py-2">
                      <DocumentStatusBadge status={v.status} />
                    </td>
                    <td className="px-3 py-2 text-slate-600">
                      {new Date(v.createdAt).toLocaleString()}
                    </td>
                    <td className="px-3 py-2 text-slate-600">{v.isLatest ? 'Yes' : '—'}</td>
                  </tr>
                ))}
                {versions.length === 0 && (
                  <tr>
                    <td colSpan={4} className="px-3 py-6 text-center text-slate-500">
                      No versions found.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
