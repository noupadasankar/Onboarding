import { useState } from 'react';
import { Link, Outlet } from 'react-router-dom';
import { Search, Bell, ChevronDown } from 'lucide-react';
import { Sidebar } from './Sidebar';
import { useAuth } from '@/features/auth/hooks/useAuth';
import { useListNotificationsQuery } from '@/features/notifications/api/notificationsApi';
import { cn } from '@/lib/utils';
import { FeatureErrorBoundary } from '@/shared/components/FeatureErrorBoundary';

export function AppLayout() {
  const { user } = useAuth();
  const [search, setSearch] = useState('');
  const { data: notifData } = useListNotificationsQuery({ pageSize: 1 });
  const unreadCount = notifData?.unreadCount ?? 0;

  const initials = user?.email ? user.email.charAt(0).toUpperCase() : '?';
  const displayName = user?.email?.split('@')[0] ?? '';
  const roleDisplay = user?.role?.replace(/_/g, ' ') ?? '';

  return (
    <div className="flex h-screen overflow-hidden bg-slate-50">
      <Sidebar />

      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top Navigation Bar */}
        <header className="z-10 flex h-16 shrink-0 items-center justify-between border-b border-slate-200 bg-white px-6 shadow-sm">
          {/* Search */}
          <div className={cn(
            'flex items-center gap-2 rounded-lg border bg-slate-50 px-3 py-2 w-80 transition-all',
            search ? 'border-teal-500 ring-1 ring-teal-500' : 'border-slate-200',
          )}>
            <Search className="h-4 w-4 shrink-0 text-slate-400" />
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="flex-1 bg-transparent text-sm text-slate-700 placeholder-slate-400 outline-none"
              placeholder="Search users, documents, chats…"
            />
          </div>

          {/* Right controls */}
          <div className="flex items-center gap-2">
            {/* AI status pill */}
            <div className="flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
              AI Online
            </div>

            {/* Notifications */}
            <Link
              to="/notifications"
              className="relative rounded-full p-2 text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-700"
            >
              <Bell className="h-5 w-5" />
              {unreadCount > 0 && (
                <span className="absolute right-0.5 top-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-[9px] font-bold text-white">
                  {unreadCount > 9 ? '9+' : unreadCount}
                </span>
              )}
            </Link>

            <div className="h-8 w-px bg-slate-200" />

            {/* User chip */}
            <Link
              to="/profile"
              className="flex items-center gap-2.5 rounded-lg px-2 py-1.5 transition-colors hover:bg-slate-100"
            >
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-teal-600 text-xs font-bold text-white shadow-sm">
                {initials}
              </div>
              <div className="flex flex-col leading-none">
                <span className="text-xs font-semibold text-slate-800">{displayName}</span>
                <span className="mt-0.5 text-[10px] text-slate-500">{roleDisplay}</span>
              </div>
              <ChevronDown className="h-3 w-3 text-slate-400" />
            </Link>
          </div>
        </header>

        {/* Page content - wrapped in feature error boundary */}
        <main className="flex-1 overflow-y-auto">
          <FeatureErrorBoundary featureName="Page content">
            <Outlet />
          </FeatureErrorBoundary>
        </main>
      </div>
    </div>
  );
}
