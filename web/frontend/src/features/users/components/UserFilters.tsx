import { useId } from 'react';
import { ALL_ROLES } from '@optiagent/shared';
import type { Role } from '@optiagent/shared';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import type { UsersFilters } from '../hooks/useUsers';

interface UserFiltersProps {
  filters: UsersFilters;
  onChange: <K extends keyof UsersFilters>(key: K, value: UsersFilters[K]) => void;
}

export function UserFilters({ filters, onChange }: UserFiltersProps) {
  const searchId = useId();
  const roleId = useId();

  return (
    <div className="flex flex-wrap items-center gap-3">
      <div className="flex flex-col gap-1">
        <label htmlFor={searchId} className="text-xs font-medium text-slate-600">
          Search
        </label>
        <Input
          id={searchId}
          placeholder="Search by email…"
          value={filters.search ?? ''}
          onChange={(e) => onChange('search', e.target.value || undefined)}
          className="w-56"
        />
      </div>

      <div className="flex flex-col gap-1">
        <label htmlFor={roleId} className="text-xs font-medium text-slate-600">
          Role
        </label>
        <Select
          id={roleId}
          value={filters.role ?? ''}
          onChange={(e) => onChange('role', (e.target.value as Role) || undefined)}
          className="w-40"
        >
          <option value="">All roles</option>
          {ALL_ROLES.map((r) => (
            <option key={r} value={r}>
              {r.replace('_', ' ')}
            </option>
          ))}
        </Select>
      </div>

      <div className="flex flex-col gap-1">
        <label className="text-xs font-medium text-slate-600">Status</label>
        <Select
          value={filters.isActive === undefined ? '' : String(filters.isActive)}
          onChange={(e) =>
            onChange(
              'isActive',
              e.target.value === '' ? undefined : e.target.value === 'true',
            )
          }
          className="w-32"
        >
          <option value="">All</option>
          <option value="true">Active</option>
          <option value="false">Inactive</option>
        </Select>
      </div>
    </div>
  );
}
