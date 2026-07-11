import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useAuth } from '@/features/auth/hooks/useAuth';

const ROLE_BADGE_VARIANT = {
  IT_ADMIN: 'brand',
  HR_MANAGER: 'success',
  FINANCE_ADMIN: 'warning',
  EMPLOYEE: 'default',
} as const;

export function ProfilePage() {
  const { user } = useAuth();

  if (!user) {
    return (
      <div className="p-6">
        <p className="text-sm text-slate-500">Not signed in.</p>
      </div>
    );
  }

  const roleBadgeVariant =
    ROLE_BADGE_VARIANT[user.role as keyof typeof ROLE_BADGE_VARIANT] ?? 'default';

  return (
    <div className="mx-auto max-w-2xl p-6">
      <h1 className="mb-6 text-2xl font-semibold text-slate-900">Your Profile</h1>

      <div className="flex flex-col gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Account details</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="flex flex-col gap-3 text-sm">
              <div className="flex items-center justify-between">
                <dt className="font-medium text-slate-600">Email</dt>
                <dd className="text-slate-900">{user.email}</dd>
              </div>

              <div className="flex items-center justify-between">
                <dt className="font-medium text-slate-600">Role</dt>
                <dd>
                  <Badge variant={roleBadgeVariant}>
                    {user.role.replace('_', ' ')}
                  </Badge>
                </dd>
              </div>

              <div className="flex items-center justify-between">
                <dt className="font-medium text-slate-600">Department</dt>
                <dd className="text-slate-900">{user.department ?? 'Not assigned'}</dd>
              </div>
            </dl>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Permissions</CardTitle>
          </CardHeader>
          <CardContent>
            {user.permissions.length === 0 ? (
              <p className="text-sm text-slate-500">No permissions assigned.</p>
            ) : (
              <ul className="flex flex-wrap gap-2">
                {user.permissions.map((p) => (
                  <li key={p}>
                    <Badge variant="default">{p}</Badge>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
