import { useState } from 'react';
import { Permission } from '@optiagent/shared';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { useAuth } from '@/features/auth/hooks/useAuth';
import {
  useListSettingsQuery,
  useUpsertSettingMutation,
  useDeleteSettingMutation,
} from '../api/adminSettingsApi';
import type { AdminSettingDTO } from '../types';

interface SettingFormState {
  key: string;
  value: string;
  description: string;
}

const EMPTY_FORM: SettingFormState = { key: '', value: '', description: '' };

function parseValue(raw: string): unknown {
  try {
    return JSON.parse(raw);
  } catch {
    return raw;
  }
}

function formatValue(value: unknown): string {
  const str = JSON.stringify(value);
  return str.length > 60 ? str.slice(0, 57) + '...' : str;
}

interface SettingModalProps {
  open: boolean;
  onClose: () => void;
  editTarget: AdminSettingDTO | null;
}

function SettingModal({ open, onClose, editTarget }: SettingModalProps) {
  const isEdit = editTarget !== null;
  const [form, setForm] = useState<SettingFormState>(EMPTY_FORM);
  const [upsertSetting, { isLoading }] = useUpsertSettingMutation();

  const handleOpenChange = (nextOpen: boolean) => {
    if (nextOpen) {
      setForm(
        editTarget
          ? {
              key: editTarget.key,
              value: JSON.stringify(editTarget.value),
              description: editTarget.description ?? '',
            }
          : EMPTY_FORM,
      );
    } else {
      onClose();
    }
  };

  const set = (field: keyof SettingFormState) => (e: React.ChangeEvent<HTMLInputElement>) => {
    setForm((prev) => ({ ...prev, [field]: e.target.value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await upsertSetting({
        key: form.key,
        value: parseValue(form.value),
        description: form.description || undefined,
      }).unwrap();
      onClose();
    } catch {
      // errors handled server-side
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{isEdit ? 'Edit Setting' : 'Add Setting'}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="setting-key">Key</Label>
            <Input
              id="setting-key"
              type="text"
              placeholder="e.g. max_upload_size"
              value={form.key}
              onChange={set('key')}
              disabled={isEdit}
              required
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="setting-value">Value (JSON or plain string)</Label>
            <Input
              id="setting-value"
              type="text"
              placeholder='e.g. 42 or "hello" or {"enabled":true}'
              value={form.value}
              onChange={set('value')}
              required
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="setting-description">Description (optional)</Label>
            <Input
              id="setting-description"
              type="text"
              placeholder="What this setting controls"
              value={form.description}
              onChange={set('description')}
            />
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose} disabled={isLoading}>
              Cancel
            </Button>
            <Button type="submit" disabled={isLoading}>
              {isLoading ? 'Saving...' : isEdit ? 'Save changes' : 'Add setting'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export function AdminSettingsPage() {
  const { hasPermission } = useAuth();
  const canManage = hasPermission(Permission.USERS_MANAGE);

  const { data, isLoading, isError } = useListSettingsQuery();
  const [deleteSetting] = useDeleteSettingMutation();

  const [addOpen, setAddOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<AdminSettingDTO | null>(null);

  const handleDelete = async (key: string) => {
    if (!window.confirm(`Delete setting "${key}"? This action cannot be undone.`)) return;
    try {
      await deleteSetting(key).unwrap();
    } catch {
      // errors handled server-side
    }
  };

  return (
    <div className="p-6">
      <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Admin Settings</h1>
          <p className="text-sm text-slate-500">Manage global platform configuration.</p>
        </div>
        {canManage && (
          <Button onClick={() => setAddOpen(true)}>Add setting</Button>
        )}
      </div>

      {isLoading && (
        <p className="py-8 text-center text-sm text-slate-500">Loading settings...</p>
      )}

      {isError && (
        <p className="py-8 text-center text-sm text-red-600">
          Failed to load settings. Please try again.
        </p>
      )}

      {data && (
        <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Key</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Value</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Description</th>
                <th className="px-4 py-3 text-left font-medium text-slate-600">Last Updated</th>
                {canManage && <th className="px-4 py-3" />}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data.map((setting) => (
                <tr key={setting.key} className="hover:bg-slate-50">
                  <td className="px-4 py-3 font-mono font-medium text-slate-900">
                    {setting.key}
                  </td>
                  <td className="px-4 py-3 font-mono text-slate-600">
                    {formatValue(setting.value)}
                  </td>
                  <td className="px-4 py-3 text-slate-500">{setting.description ?? '—'}</td>
                  <td className="px-4 py-3 text-slate-500">
                    {new Date(setting.updatedAt).toLocaleDateString()}
                  </td>
                  {canManage && (
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setEditTarget(setting)}
                        >
                          Edit
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-red-600 hover:bg-red-50 hover:text-red-700"
                          onClick={() => handleDelete(setting.key)}
                        >
                          Delete
                        </Button>
                      </div>
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
                    No settings configured.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      <SettingModal
        open={addOpen}
        onClose={() => setAddOpen(false)}
        editTarget={null}
      />

      <SettingModal
        open={Boolean(editTarget)}
        onClose={() => setEditTarget(null)}
        editTarget={editTarget}
      />
    </div>
  );
}
