import { useMemo } from 'react';
import type { Permission } from '@optiagent/shared';
import { useAppDispatch, useAppSelector } from '@/app/hooks';
import { useLogoutMutation } from '../api/authApi';
import { clearCredentials } from '../redux/authSlice';

/** Convenience facade over the auth slice: identity, permission checks, logout. */
export function useAuth() {
  const dispatch = useAppDispatch();
  const { user, accessToken, refreshToken } = useAppSelector((s) => s.auth);
  const [logoutMutation] = useLogoutMutation();

  const permissions = useMemo(() => new Set(user?.permissions ?? []), [user]);

  const logout = async (): Promise<void> => {
    try {
      if (refreshToken) await logoutMutation({ refreshToken }).unwrap();
    } finally {
      dispatch(clearCredentials());
    }
  };

  return {
    user,
    isAuthenticated: Boolean(accessToken && user),
    hasPermission: (p: Permission) => permissions.has(p),
    logout,
  };
}
