import { createBrowserRouter, Navigate } from 'react-router-dom';
import { Permission } from '@optiagent/shared';
import { AppLayout } from '@/layouts/AppLayout';
import { LoginPage } from '@/features/auth/pages/LoginPage';
import { DashboardPage } from '@/features/dashboard/pages/DashboardPage';
import { UserListPage } from '@/features/users/pages/UserListPage';
import { ChatPage } from '@/features/chat/pages/ChatPage';
import { DocumentListPage } from '@/features/documents/pages/DocumentListPage';
import { DepartmentsPage } from '@/features/departments/pages/DepartmentsPage';
import { AnalyticsPage } from '@/features/analytics/pages/AnalyticsPage';
import { NotificationsPage } from '@/features/notifications/pages/NotificationsPage';
import { ProfilePage } from '@/features/profile/pages/ProfilePage';
import { AdminSettingsPage } from '@/features/admin-settings/pages/AdminSettingsPage';
import { ProtectedRoute } from './ProtectedRoute';

export const router = createBrowserRouter([
  { path: '/', element: <Navigate to="/dashboard" replace /> },
  { path: '/login', element: <LoginPage /> },

  {
    // All authenticated routes share the AppLayout shell (sidebar + main).
    element: <AppLayout />,
    children: [
      {
        path: '/dashboard',
        element: (
          <ProtectedRoute>
            <DashboardPage />
          </ProtectedRoute>
        ),
      },
      {
        path: '/users',
        element: (
          <ProtectedRoute permission={Permission.USERS_READ}>
            <UserListPage />
          </ProtectedRoute>
        ),
      },
      {
        path: '/chat',
        element: <ProtectedRoute><ChatPage /></ProtectedRoute>,
      },
      {
        path: '/documents',
        element: <ProtectedRoute permission={Permission.DOCUMENTS_UPLOAD}><DocumentListPage /></ProtectedRoute>,
      },
      {
        path: '/departments',
        element: <ProtectedRoute><DepartmentsPage /></ProtectedRoute>,
      },
      {
        path: '/analytics',
        element: <ProtectedRoute permission={Permission.GOVERNANCE_READ}><AnalyticsPage /></ProtectedRoute>,
      },
      {
        path: '/notifications',
        element: <ProtectedRoute><NotificationsPage /></ProtectedRoute>,
      },
      {
        path: '/profile',
        element: <ProtectedRoute><ProfilePage /></ProtectedRoute>,
      },
      {
        path: '/admin/settings',
        element: <ProtectedRoute permission={Permission.USERS_MANAGE}><AdminSettingsPage /></ProtectedRoute>,
      },
    ],
  },

  {
    path: '/forbidden',
    element: (
      <div className="flex h-screen items-center justify-center p-8 text-center text-slate-600">
        <div>
          <h1 className="text-xl font-semibold">403 — Forbidden</h1>
          <p>You do not have permission to view this page.</p>
        </div>
      </div>
    ),
  },
  { path: '*', element: <Navigate to="/dashboard" replace /> },
]);
