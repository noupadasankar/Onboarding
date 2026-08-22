import { useState } from 'react';
import { Permission } from '@hr-onboarding/shared';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { useAuth } from '@/features/auth/hooks/useAuth';
import {
  useListDepartmentsQuery,
  useCreateDepartmentMutation,
  useUpdateDepartmentMutation,
} from '../api/departmentsApi';
import type { DepartmentDTO } from '../types';

interface DeptFormState {
  name: string;
  displayName: string;
  description: string;
  isActive: boolean;
}

const EMPTY_FORM: DeptFormState = {
  name: '',
  displayName: '',
  description: '',
  isActive: true,
};

interface DeptModalProps {
  open: boolean;
  onClose: () => void;
  editTarget: DepartmentDTO | null;
}

function DeptModal({ open, onClose, editTarget }: DeptModalProps) {
  const isEdit = editTarget !== null;
  const [form, setForm] = useState<DeptFormState>(EMPTY_FORM);
  const [createDepartment, { isLoading: creating }] = useCreateDepartmentMutation();
  const [updateDepartment, { isLoading: updating }] = useUpdateDepartmentMutation();
  const isLoading = creating || updating;

  // Sync form when modal opens
  const handleOpenChange = (nextOpen: boolean) => {
    if (nextOpen) {
      setForm(
        editTarget
          ? {
              name: editTarget.name,
              displayName: editTarget.displayName,
              description: editTarget.description ?? '',
              isActive: editTarget.isActive,
            }
          : EMPTY_FORM,
      );
    } else {
      onClose();
    }
  };

  // Also reset when editTarget changes while open
  const syncedForm = (() => form)();

  const set = (field: keyof DeptFormState) => (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = field === 'isActive' ? e.target.checked : e.target.value;
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (isEdit && editTarget) {
        await updateDepartment({
          id: editTarget.id,
          body: {
            name: syncedForm.name,
            displayName: syncedForm.displayName,
            description: syncedForm.description || undefined,
            isActive: syncedForm.isActive,
          },
        }).unwrap();
      } else {
        await createDepartment({
          name: syncedForm.name,
          displayName: syncedForm.displayName,
          description: syncedForm.description || undefined,
        }).unwrap();
      }
      onClose();
    } catch {
      // errors handled server-side
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{isEdit ? 'Edit Department' : 'Create Department'}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="dept-name">Name</Label>
            <Input
              id="dept-name"
              type="text"
              placeholder="e.g. engineering"
              value={form.name}
              onChange={set('name')}
              required
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="dept-display-name">Display Name</Label>
            <Input
              id="dept-display-name"
              type="text"
              placeholder="e.g. Engineering"
              value={form.displayName}
              onChange={set('displayName')}
              required
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="dept-description">Description (optional)</Label>
            <Input
              id="dept-description"
              type="text"
              placeholder="Short description"
              value={form.description}
              onChange={set('description')}
            />
          </div>

          {isEdit && (
            <div className="flex items-center gap-2">
              <input
                id="dept-active"
                type="checkbox"
                checked={form.isActive}
                onChange={set('isActive')}
                className="h-4 w-4 rounded border-slate-300"
              />
              <Label htmlFor="dept-active">Active</Label>
            </div>
          )}

          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose} disabled={isLoading}>
              Cancel
            </Button>
            <Button type="submit" disabled={isLoading}>
              {isLoading ? 'Saving...' : isEdit ? 'Save changes' : 'Create department'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export function DepartmentsPage() {
  const { hasPermission } = useAuth();
  const canManage = hasPermission(Permission.USERS_MANAGE);

  const { data, isLoading, isError } = useListDepartmentsQuery();

  const [createOpen, setCreateOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<DepartmentDTO | null>(null);

  return (
    <div className="p-6">
      <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Departments</h1>
          <p className="text-sm text-slate-500">Manage organisation departments.</p>
        </div>
        {canManage && (
          <Button onClick={() => setCreateOpen(true)}>Create department</Button>
        )}
      </div>

      {isLoading && (
        <p className="py-8 text-center text-sm text-slate-500">Loading departments...</p>
      )}

      {isError && (
        <p className="py-8 text-center text-sm text-red-600">
          Failed to load departments. Please try again.
        </p>
      )}

      {data && (
        <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Name</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Display Name</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Description</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Status</th>
                {canManage && <th className="px-4 py-3" />}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data.map((dept) => (
                <tr key={dept.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3 font-medium text-slate-900">{dept.name}</td>
                  <td className="px-4 py-3 text-slate-700">{dept.displayName}</td>
                  <td className="px-4 py-3 text-slate-500">{dept.description ?? '—'}</td>
                  <td className="px-4 py-3">
                    <Badge variant={dept.isActive ? 'success' : 'danger'}>
                      {dept.isActive ? 'Active' : 'Inactive'}
                    </Badge>
                  </td>
                  {canManage && (
                    <td className="px-4 py-3 text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setEditTarget(dept)}
                      >
                        Edit
                      </Button>
                    </td>
                  )}
                </tr>
              ))}
              {data.length === 0 && (
                <tr>
                  <td
                    colSpan={canManage ? 5 : 4}
                    className="px-4 py-8 text-center text-slate-500"
                  >
                    No departments found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      <DeptModal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        editTarget={null}
      />

      <DeptModal
        open={Boolean(editTarget)}
        onClose={() => setEditTarget(null)}
        editTarget={editTarget}
      />
    </div>
  );
}
