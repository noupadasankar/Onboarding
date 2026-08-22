import { useRef, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Dialog, DialogContent, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { useAuth } from '@/features/auth/hooks/useAuth';
import { useUploadDocumentMutation } from '../api/documentsApi';

interface Department {
  id: string;
  name: string;
  displayName: string;
}

interface UploadDocumentModalProps {
  open: boolean;
  onClose: () => void;
  /** Kept for API compatibility; department is now derived from the user's role. */
  departments?: Department[];
}

/** Human-readable department a role uploads into (mirrors backend role→dept map). */
const ROLE_DEPARTMENT_LABEL: Record<string, string> = {
  HR_MANAGER: 'HR',
  FINANCE_ADMIN: 'Finance',
  IT_ADMIN: 'IT',
};

export function UploadDocumentModal({ open, onClose }: UploadDocumentModalProps) {
  const { user } = useAuth();
  const [uploadDocument, { isLoading }] = useUploadDocumentMutation();
  const fileRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);

  const departmentLabel = user ? ROLE_DEPARTMENT_LABEL[user.role] ?? '—' : '—';

  const handleClose = () => {
    setError(null);
    if (fileRef.current) fileRef.current.value = '';
    onClose();
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError(null);

    const file = fileRef.current?.files?.[0];
    if (!file) {
      setError('Please select a file to upload.');
      return;
    }

    // Department is assigned server-side from the caller's role — not sent here.
    const formData = new FormData();
    formData.append('file', file);

    try {
      await uploadDocument(formData).unwrap();
      handleClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed. Please try again.');
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} data-testid="upload-document-modal">
      <DialogContent>
        <DialogTitle>Upload Document</DialogTitle>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="file">File</Label>
          <input
            id="file"
            ref={fileRef}
            type="file"
            accept=".pdf,.docx,.txt,.csv,.xlsx"
            data-testid="upload-file-input"
            className="block w-full text-sm text-slate-700 file:mr-4 file:rounded-md file:border-0 file:bg-slate-100 file:px-3 file:py-2 file:text-sm file:font-medium file:text-slate-700 hover:file:bg-slate-200"
          />
          <p className="text-xs text-slate-500">Accepted: PDF, DOCX, TXT, CSV, XLSX</p>
        </div>

        <div className="flex flex-col gap-1.5">
          <Label>Department</Label>
          <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">
            {departmentLabel}
          </div>
          <p className="text-xs text-slate-500">
            Documents are filed under your department automatically.
          </p>
        </div>

        {error && (
          <p role="alert" className="text-sm text-red-600" data-testid="upload-error">
            {error}
          </p>
        )}

        <DialogFooter>
          <Button type="button" variant="outline" onClick={handleClose} disabled={isLoading} data-testid="upload-cancel">
            Cancel
          </Button>
          <Button type="submit" disabled={isLoading} data-testid="upload-submit">
            {isLoading ? 'Uploading…' : 'Upload'}
          </Button>
        </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
