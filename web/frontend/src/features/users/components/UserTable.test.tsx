import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Provider } from 'react-redux';
import { MemoryRouter } from 'react-router-dom';
import { configureStore } from '@reduxjs/toolkit';
import { baseApi } from '@/app/api/baseApi';
import authReducer from '@/features/auth/redux/authSlice';
import { Role, Permission } from '@optiagent/shared';
import type { UserDTO } from '@optiagent/shared';
import { UserTable } from './UserTable';

/** Build a minimal store with a seeded auth state. */
function makeStore(role: Role) {
  return configureStore({
    reducer: { auth: authReducer, [baseApi.reducerPath]: baseApi.reducer },
    middleware: (get) => get().concat(baseApi.middleware),
    preloadedState: {
      auth: {
        user: {
          id: 'u_1',
          email: 'test@optiagent.dev',
          role,
          department: null,
          permissions: role === Role.IT_ADMIN
            ? [Permission.USERS_READ, Permission.USERS_WRITE, Permission.IT_QUERY, Permission.GOVERNANCE_READ]
            : [Permission.USERS_READ, Permission.HR_QUERY, Permission.IT_QUERY, Permission.GOVERNANCE_READ],
        },
        accessToken: 'token',
        refreshToken: 'refresh',
      },
    },
  });
}

function makeUsers(count = 3): UserDTO[] {
  return Array.from({ length: count }, (_, i) => ({
    id: `u_${i}`,
    email: `user${i}@optiagent.dev`,
    role: Role.EMPLOYEE,
    department: 'Engineering',
    isActive: true,
    createdAt: new Date().toISOString(),
  }));
}

function renderTable(role: Role, users: UserDTO[]) {
  const store = makeStore(role);
  return render(
    <Provider store={store}>
      <MemoryRouter>
        <UserTable
          data={{ items: users, total: users.length, page: 1, pageSize: 20 }}
          onEdit={vi.fn()}
          onDeactivate={vi.fn()}
          onPageChange={vi.fn()}
        />
      </MemoryRouter>
    </Provider>,
  );
}

describe('UserTable', () => {
  it('renders the correct number of rows', () => {
    renderTable(Role.HR_MANAGER, makeUsers(3));
    // Header row + 3 data rows
    expect(screen.getAllByRole('row')).toHaveLength(4);
  });

  it('shows "No users found" when the list is empty', () => {
    renderTable(Role.HR_MANAGER, []);
    expect(screen.getByText(/no users found/i)).toBeInTheDocument();
  });

  it('shows action menu for IT_ADMIN (has users:write)', () => {
    renderTable(Role.IT_ADMIN, makeUsers(1));
    expect(screen.getByRole('button', { name: '···' })).toBeInTheDocument();
  });

  it('hides action menu for HR_MANAGER (lacks users:write)', () => {
    renderTable(Role.HR_MANAGER, makeUsers(1));
    expect(screen.queryByRole('button', { name: '···' })).not.toBeInTheDocument();
  });

  it('displays role badge for each user', () => {
    renderTable(Role.IT_ADMIN, makeUsers(2));
    const badges = screen.getAllByText(/EMPLOYEE/);
    expect(badges.length).toBeGreaterThanOrEqual(2);
  });
});
