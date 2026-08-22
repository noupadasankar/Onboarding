import { useState } from 'react';
import type { UserDTO } from '@hr-onboarding/shared';
import { Permission } from '@hr-onboarding/shared';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/features/auth/hooks/useAuth';
import { useUsers } from '../hooks/useUsers';
import { UserFilters } from '../components/UserFilters';
import { UserTable } from '../components/UserTable';
import { UserFormModal } from '../components/UserFormModal';
import { DeactivateConfirmDialog } from '../components/DeactivateConfirmDialog';

export function UserListPage() {
  const { hasPermission } = useAuth();
  const { filters, setFilter, data, isLoading, isError } = useUsers();

  const [createOpen, setCreateOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<UserDTO | null>(null);
  const [deactivateTarget, setDeactivateTarget] = useState<UserDTO | null>(null);

  return (
    <div className="p-6">
      <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Users</h1>
          <p className="text-sm text-slate-500">Manage platform users and their roles.</p>
        </div>
        {hasPermission(Permission.USERS_WRITE) && (
          <Button onClick={() => setCreateOpen(true)}>Create user</Button>
        )}
      </div>

      <div className="mb-4">
        <UserFilters filters={filters} onChange={setFilter} />
      </div>

      {isLoading && (
        <p className="py-8 text-center text-sm text-slate-500">Loading users…</p>
      )}

      {isError && (
        <p className="py-8 text-center text-sm text-red-600">
          Failed to load users. Please try again.
        </p>
      )}

      {data && (
        <UserTable
          data={data}
          onEdit={(user) => setEditTarget(user)}
          onDeactivate={(user) => setDeactivateTarget(user)}
          onPageChange={(page) => setFilter('page', page)}
        />
      )}

      <UserFormModal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
      />

      <UserFormModal
        open={Boolean(editTarget)}
        onClose={() => setEditTarget(null)}
        initialValues={editTarget ?? undefined}
      />

      <DeactivateConfirmDialog
        open={Boolean(deactivateTarget)}
        user={deactivateTarget}
        onClose={() => setDeactivateTarget(null)}
      />
    </div>
  );
}
