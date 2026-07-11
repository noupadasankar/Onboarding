import { useState } from 'react';
import type { Paginated, UserDTO } from '@optiagent/shared';
import { Permission } from '@optiagent/shared';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/features/auth/hooks/useAuth';

const ROLE_BADGE_VARIANT = {
  IT_ADMIN: 'brand',
  HR_MANAGER: 'success',
  FINANCE_ADMIN: 'warning',
  EMPLOYEE: 'default',
} as const;

interface ActionMenuProps {
  user: UserDTO;
  onEdit: (user: UserDTO) => void;
  onDeactivate: (user: UserDTO) => void;
}

function ActionMenu({ user, onEdit, onDeactivate }: ActionMenuProps) {
  const [open, setOpen] = useState(false);
  const { hasPermission } = useAuth();
  if (!hasPermission(Permission.USERS_WRITE)) return null;

  return (
    <div className="relative">
      <Button
        variant="ghost"
        size="sm"
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="menu"
      >
        ···
      </Button>
      {open && (
        <div
          className="absolute right-0 z-10 mt-1 w-32 rounded-md border border-slate-200 bg-white py-1 shadow-lg"
          onMouseLeave={() => setOpen(false)}
        >
          <button
            className="w-full px-4 py-2 text-left text-sm text-slate-700 hover:bg-slate-50"
            onClick={() => { setOpen(false); onEdit(user); }}
          >
            Edit
          </button>
          {user.isActive && (
            <button
              className="w-full px-4 py-2 text-left text-sm text-red-600 hover:bg-red-50"
              onClick={() => { setOpen(false); onDeactivate(user); }}
            >
              Deactivate
            </button>
          )}
        </div>
      )}
    </div>
  );
}

interface UserTableProps {
  data: Paginated<UserDTO>;
  onEdit: (user: UserDTO) => void;
  onDeactivate: (user: UserDTO) => void;
  onPageChange: (page: number) => void;
}

export function UserTable({ data, onEdit, onDeactivate, onPageChange }: UserTableProps) {
  const totalPages = Math.ceil(data.total / data.pageSize);

  return (
    <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
      <table className="min-w-full divide-y divide-slate-200 text-sm">
        <thead className="bg-slate-50">
          <tr>
            <th className="px-4 py-3 text-left font-medium text-slate-600">Email</th>
            <th className="px-4 py-3 text-left font-medium text-slate-600">Role</th>
            <th className="px-4 py-3 text-left font-medium text-slate-600">Department</th>
            <th className="px-4 py-3 text-left font-medium text-slate-600">Status</th>
            <th className="px-4 py-3" />
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {data.items.map((user) => (
            <tr key={user.id} className="hover:bg-slate-50">
              <td className="px-4 py-3 font-medium text-slate-900">{user.email}</td>
              <td className="px-4 py-3">
                <Badge variant={ROLE_BADGE_VARIANT[user.role as keyof typeof ROLE_BADGE_VARIANT] ?? 'default'}>
                  {user.role.replace('_', ' ')}
                </Badge>
              </td>
              <td className="px-4 py-3 text-slate-600">{user.department ?? '—'}</td>
              <td className="px-4 py-3">
                <Badge variant={user.isActive ? 'success' : 'danger'}>
                  {user.isActive ? 'Active' : 'Inactive'}
                </Badge>
              </td>
              <td className="px-4 py-3 text-right">
                <ActionMenu user={user} onEdit={onEdit} onDeactivate={onDeactivate} />
              </td>
            </tr>
          ))}
          {data.items.length === 0 && (
            <tr>
              <td colSpan={5} className="px-4 py-8 text-center text-slate-500">
                No users found.
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
              onClick={() => onPageChange(data.page - 1)}
            >
              Prev
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={data.page >= totalPages}
              onClick={() => onPageChange(data.page + 1)}
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
