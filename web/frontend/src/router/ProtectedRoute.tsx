import type { ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import type { Permission } from '@optiagent/shared';
import { useAuth } from '@/features/auth/hooks/useAuth';
import { FeatureErrorBoundary } from '@/shared/components/FeatureErrorBoundary';

interface ProtectedRouteProps {
  children: ReactNode;
  /** Optional permission gate; when set, the principal must hold it. */
  permission?: Permission;
}

/**
 * Guards a route: unauthenticated users are redirected to /login (remembering
 * where they were headed); authenticated-but-unauthorized users get /forbidden.
 * Wraps children in a FeatureErrorBoundary to prevent feature crashes from
 * taking down the entire app.
 */
export function ProtectedRoute({ children, permission }: ProtectedRouteProps) {
  const { isAuthenticated, hasPermission } = useAuth();
  const location = useLocation();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }
  if (permission && !hasPermission(permission)) {
    return <Navigate to="/forbidden" replace />;
  }
  return (
    <FeatureErrorBoundary featureName="Protected feature">
      {children}
    </FeatureErrorBoundary>
  );
}
