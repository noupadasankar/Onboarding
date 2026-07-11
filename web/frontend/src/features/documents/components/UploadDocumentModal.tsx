import { useRef, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Select } from '@/components/ui/select';
import { Dialog, DialogContent, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { useUploadDocumentMutation } from '../api/documentsApi';

interface Department {
  id: string;
  name: string;
  displayName: string;
}

interface UploadDocumentModalProps {
  open: boolean;
  onClose: () => void;
  departments: Department[];
}

export function UploadDocumentModal({ open, onClose, departments }: UploadDocumentModalProps) {
  const [uploadDocument, { isLoading }] = useUploadDocumentMutation();
  const fileRef = useRef<HTMLInputElement>(null);
  const [departmentId, setDepartmentId] = useState('');
  const [error, setError] = useState<string | null>(null);

  const handleClose = () => {
    setDepartmentId('');
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

    const formData = new FormData();
    formData.append('file', file);
    if (departmentId) {
      formData.append('departmentId', departmentId);
    }

    try {
      await uploadDocument(formData).unwrap();
      handleClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed. Please try again.');
    }
  };

  return (
    <Dialog open={open} onClose={handleClose}>
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
            className="block w-full text-sm text-slate-700 file:mr-4 file:rounded-md file:border-0 file:bg-slate-100 file:px-3 file:py-2 file:text-sm file:font-medium file:text-slate-700 hover:file:bg-slate-200"
          />
          <p className="text-xs text-slate-500">Accepted: PDF, DOCX, TXT, CSV, XLSX</p>
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="departmentId">Department (optional)</Label>
          <Select
            id="departmentId"
            value={departmentId}
            onChange={(e) => setDepartmentId(e.target.value)}
          >
            <option value="">No department</option>
            {departments.map((dept) => (
              <option key={dept.id} value={dept.id}>
                {dept.displayName}
              </option>
            ))}
          </Select>
        </div>

        {error && (
          <p role="alert" className="text-sm text-red-600">
            {error}
          </p>
        )}

        <DialogFooter>
          <Button type="button" variant="outline" onClick={handleClose} disabled={isLoading}>
            Cancel
          </Button>
          <Button type="submit" disabled={isLoading}>
            {isLoading ? 'Uploading…' : 'Upload'}
          </Button>
        </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
