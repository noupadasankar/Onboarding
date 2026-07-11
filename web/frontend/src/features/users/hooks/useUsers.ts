import { useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { ALL_ROLES } from '@optiagent/shared';
import type { Role } from '@optiagent/shared';
import { useListUsersQuery } from '../api/usersApi';

export interface UsersFilters {
  search?: string;
  role?: Role;
  isActive?: boolean;
  page: number;
  pageSize: number;
}

function parseFilters(params: URLSearchParams): UsersFilters {
  const rawPage = parseInt(params.get('page') ?? '1', 10);
  const rawSize = parseInt(params.get('pageSize') ?? '20', 10);
  const rawRole = params.get('role');
  return {
    page: Number.isFinite(rawPage) && rawPage >= 1 ? rawPage : 1,
    pageSize: Number.isFinite(rawSize) && rawSize >= 1 ? rawSize : 20,
    search: params.get('search') ?? undefined,
    role:
      rawRole && (ALL_ROLES as readonly string[]).includes(rawRole)
        ? (rawRole as Role)
        : undefined,
    isActive: params.has('isActive') ? params.get('isActive') === 'true' : undefined,
  };
}

/** Composes the RTK Query list endpoint with URL-backed filter/pagination state. */
export function useUsers() {
  const [searchParams, setSearchParams] = useSearchParams();
  const filters = parseFilters(searchParams);

  const query = useListUsersQuery({
    page: filters.page,
    pageSize: filters.pageSize,
    search: filters.search,
    role: filters.role,
    isActive: filters.isActive,
  });

  const setFilter = useCallback(
    <K extends keyof UsersFilters>(key: K, value: UsersFilters[K]) => {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        if (value === undefined || value === '') {
          next.delete(key);
        } else {
          next.set(key, String(value));
        }
        if (key !== 'page') next.delete('page');
        return next;
      });
    },
    [setSearchParams],
  );

  return { filters, setFilter, ...query };
}
