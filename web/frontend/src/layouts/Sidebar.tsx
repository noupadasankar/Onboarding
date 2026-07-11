import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  MessageSquare,
  FileText,
  Building2,
  Users,
  BarChart2,
  Bell,
  User,
  Settings,
  LogOut,
  Zap,
} from 'lucide-react';
import { Permission } from '@optiagent/shared';
import { useAuth } from '@/features/auth/hooks/useAuth';
import { cn } from '@/lib/utils';
import { useListNotificationsQuery } from '@/features/notifications/api/notificationsApi';

const ROLE_PILL: Record<string, string> = {
  IT_ADMIN:     'bg-blue-100 text-blue-700',
  HR_MANAGER:   'bg-emerald-100 text-emerald-700',
  FINANCE_ADMIN:'bg-amber-100 text-amber-700',
  EMPLOYEE:     'bg-slate-100 text-slate-600',
};

function Section({ label }: { label: string }) {
  return (
    <p className="mb-1 mt-5 px-2 text-[10px] font-semibold uppercase tracking-widest text-slate-400 first:mt-0">
      {label}
    </p>
  );
}

export function Sidebar() {
  const { user, hasPermission, logout } = useAuth();
  const { data: notifData } = useListNotificationsQuery({ pageSize: 1 });
  const unreadCount = notifData?.unreadCount ?? 0;

  const navLink = ({ isActive }: { isActive: boolean }) =>
    cn(
      'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all',
      isActive
        ? 'bg-teal-700 text-white shadow-sm'
        : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900',
    );

  const rolePill = ROLE_PILL[user?.role ?? ''] ?? ROLE_PILL.EMPLOYEE;

  return (
    <aside className="flex h-full w-60 shrink-0 flex-col border-r border-slate-200 bg-white">
      {/* ── Logo ── */}
      <div className="flex h-16 items-center gap-3 border-b border-slate-100 px-5">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-teal-600 shadow-sm">
          <Zap className="h-4 w-4 fill-white text-white" />
        </div>
        <div className="flex flex-col leading-none">
          <span className="text-sm font-bold text-slate-900">OptiAgent</span>
          <span className="text-[10px] text-slate-400">Enterprise AI Platform</span>
        </div>
      </div>

      {/* ── Navigation ── */}
      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-0.5">
        <Section label="Core" />

        <NavLink to="/dashboard" className={navLink}>
          <LayoutDashboard className="h-4 w-4 shrink-0" />
          Dashboard
        </NavLink>

        <NavLink to="/chat" className={navLink}>
          <MessageSquare className="h-4 w-4 shrink-0" />
          AI Assistant
        </NavLink>

        <Section label="Workspace" />

        {hasPermission(Permission.DOCUMENTS_UPLOAD) && (
          <NavLink to="/documents" className={navLink}>
            <FileText className="h-4 w-4 shrink-0" />
            Documents
          </NavLink>
        )}

        <NavLink to="/departments" className={navLink}>
          <Building2 className="h-4 w-4 shrink-0" />
          Departments
        </NavLink>

        {hasPermission(Permission.USERS_READ) && (
          <NavLink to="/users" className={navLink}>
            <Users className="h-4 w-4 shrink-0" />
            Users
          </NavLink>
        )}

        {hasPermission(Permission.GOVERNANCE_READ) && (
          <>
            <Section label="Insights" />
            <NavLink to="/analytics" className={navLink}>
              <BarChart2 className="h-4 w-4 shrink-0" />
              Analytics
            </NavLink>
          </>
        )}

        <Section label="Account" />

        <NavLink to="/notifications" className={navLink}>
          <Bell className="h-4 w-4 shrink-0" />
          Notifications
          {unreadCount > 0 && (
            <span className="ml-auto flex h-4 min-w-[1rem] items-center justify-center rounded-full bg-red-500 px-1 text-[9px] font-bold text-white">
              {unreadCount}
            </span>
          )}
        </NavLink>

        <NavLink to="/profile" className={navLink}>
          <User className="h-4 w-4 shrink-0" />
          Profile
        </NavLink>

        {hasPermission(Permission.USERS_MANAGE) && (
          <NavLink to="/admin/settings" className={navLink}>
            <Settings className="h-4 w-4 shrink-0" />
            Admin Settings
          </NavLink>
        )}
      </nav>

      {/* ── User footer ── */}
      {user && (
        <div className="border-t border-slate-100 p-3">
          <div className="flex items-center gap-3 rounded-lg px-2 py-2">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-teal-600 text-xs font-bold text-white">
              {user.email.charAt(0).toUpperCase()}
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-xs font-semibold text-slate-800">{user.email}</p>
              <span className={cn('mt-0.5 inline-flex rounded px-1.5 py-0.5 text-[9px] font-semibold', rolePill)}>
                {user.role.replace(/_/g, ' ')}
              </span>
            </div>
            <button
              onClick={() => void logout()}
              title="Sign out"
              className="shrink-0 rounded-md p-1.5 text-slate-400 transition-colors hover:bg-red-50 hover:text-red-600"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}
    </aside>
  );
}
