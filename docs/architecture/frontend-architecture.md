# Frontend Architecture

OptiAgent — React 19 Application

---

## Table of Contents

1. [Feature-First Folder Structure](#feature-first-folder-structure)
2. [RTK Query and baseApi](#rtk-query-and-baseapi)
3. [Auth State in Redux](#auth-state-in-redux)
4. [Permission-Based UI Gating](#permission-based-ui-gating)
5. [URL-Synced Filter State](#url-synced-filter-state)
6. [AppLayout Shell](#applayout-shell)

---

## Feature-First Folder Structure

The frontend is organized by feature rather than by technical role. Each feature folder is self-contained: it owns its API slice, its components, its hooks, and its route definitions. Shared infrastructure (the Redux store, the base API, shared components) lives in a top-level `shared/` folder.

```
src/
├── features/
│   ├── auth/
│   │   ├── api/
│   │   │   └── authApi.ts            # RTK Query endpoints: login, logout, refresh, me
│   │   ├── components/
│   │   │   ├── LoginForm.tsx
│   │   │   └── ProtectedRoute.tsx
│   │   ├── hooks/
│   │   │   └── useAuth.ts            # Exposes auth state and hasPermission()
│   │   └── store/
│   │       └── authSlice.ts          # Redux slice: accessToken, refreshToken, permissions
│   │
│   ├── users/
│   │   ├── api/
│   │   │   └── usersApi.ts           # RTK Query endpoints: listUsers, getUser, createUser, etc.
│   │   ├── components/
│   │   │   ├── UsersTable.tsx
│   │   │   ├── UserForm.tsx
│   │   │   └── UserRolesBadge.tsx
│   │   ├── hooks/
│   │   │   └── useUserFilters.ts     # URL-synced filter state
│   │   └── pages/
│   │       ├── UsersPage.tsx
│   │       └── UserDetailPage.tsx
│   │
│   └── ... (documents, ai — planned)
│
├── shared/
│   ├── api/
│   │   └── baseApi.ts                # RTK Query createApi with baseQuery + re-auth
│   ├── components/
│   │   ├── AppLayout.tsx             # Shell: sidebar, topbar, outlet
│   │   ├── Sidebar.tsx               # Permission-aware nav items
│   │   ├── DataTable.tsx
│   │   └── PermissionGate.tsx        # Renders children only if permission held
│   ├── hooks/
│   │   └── useUrlParams.ts           # Typed URL search param sync utility
│   └── store/
│       └── store.ts                  # Redux store: combines reducers, configures middleware
│
├── router/
│   └── index.tsx                     # React Router: routes, layout wrapping, guards
│
└── main.tsx                          # App entry point: Provider, RouterProvider
```

### Conventions

- Each feature's `api/` file injects endpoints into `baseApi` using `baseApi.injectEndpoints()`. This keeps all endpoints on a single `baseApi` instance (shared cache, shared re-auth logic) while keeping endpoint definitions co-located with the feature.
- Pages are thin: they read URL params, call RTK Query hooks, and compose components. Business logic lives in hooks and services, not page components.
- There are no barrel re-exports from feature folders into `shared/`. Dependencies flow inward: features may import from `shared/`, but `shared/` never imports from a feature.

---

## RTK Query and baseApi

All API communication runs through a single RTK Query `createApi` instance called `baseApi`.

### baseQuery with Re-Authentication

The `baseQuery` is wrapped with `fetchBaseQuery` and a custom `baseQueryWithReAuth` wrapper that handles 401 responses by attempting a silent token refresh before retrying the original request:

```typescript
// src/shared/api/baseApi.ts (simplified)
const rawBaseQuery = fetchBaseQuery({
  baseUrl: '/api/v1',
  prepareHeaders: (headers, { getState }) => {
    const token = (getState() as RootState).auth.accessToken;
    if (token) headers.set('Authorization', `Bearer ${token}`);
    return headers;
  },
});

const baseQueryWithReAuth: BaseQueryFn = async (args, api, extraOptions) => {
  let result = await rawBaseQuery(args, api, extraOptions);

  if (result.error?.status === 401) {
    // Attempt silent refresh
    const refreshResult = await rawBaseQuery(
      { url: '/auth/refresh', method: 'POST', body: { refreshToken: selectRefreshToken(api.getState()) } },
      api,
      extraOptions,
    );

    if (refreshResult.data) {
      api.dispatch(setCredentials(refreshResult.data));
      result = await rawBaseQuery(args, api, extraOptions);
    } else {
      api.dispatch(logout());
    }
  }

  return result;
};

export const baseApi = createApi({
  reducerPath: 'api',
  baseQuery: baseQueryWithReAuth,
  tagTypes: ['User', 'Role', 'Permission', 'AuditLog', 'Document'],
  endpoints: () => ({}),
});
```

### Tag-Based Cache Invalidation

Each endpoint declares which tags it provides (queries) or invalidates (mutations):

```typescript
// src/features/users/api/usersApi.ts
export const usersApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    listUsers: builder.query({
      query: (params) => ({ url: '/users', params }),
      providesTags: (result) => [
        { type: 'User', id: 'LIST' },
        ...(result?.data ?? []).map((u) => ({ type: 'User' as const, id: u.id })),
      ],
    }),

    createUser: builder.mutation({
      query: (body) => ({ url: '/users', method: 'POST', body }),
      invalidatesTags: [{ type: 'User', id: 'LIST' }],
    }),

    updateUser: builder.mutation({
      query: ({ id, ...body }) => ({ url: `/users/${id}`, method: 'PATCH', body }),
      invalidatesTags: (_result, _err, { id }) => [
        { type: 'User', id },
        { type: 'User', id: 'LIST' },
      ],
    }),
  }),
});
```

Mutations invalidate only the tags they affect. A `PATCH /users/:id` does not invalidate Role or Permission caches.

---

## Auth State in Redux

The `authSlice` holds the current session state. It is the single source of truth for authentication throughout the application.

### State Shape

```typescript
interface AuthState {
  accessToken:  string | null;
  refreshToken: string | null;
  user: {
    id:          string;
    email:       string;
    displayName: string;
    roles:       string[];
  } | null;
  permissions: string[];   // Resolved permission strings from JWT payload
  isAuthenticated: boolean;
}
```

### Key Actions

| Action | Effect |
|---|---|
| `setCredentials({ accessToken, refreshToken, user })` | Stores token pair and user. Decodes `permissions[]` from JWT payload. Sets `isAuthenticated: true`. |
| `logout()` | Clears all auth state. RTK Query cache is reset via `baseApi.util.resetApiState()`. |
| `tokenRefreshed({ accessToken, refreshToken })` | Updates token pair after a silent refresh. Re-decodes permissions from new access token. |

### Persistence

The refresh token is persisted to `sessionStorage` (not `localStorage`) so it survives a browser tab refresh but not a browser close. The access token is held only in Redux memory (never in storage) and is lost on tab close, which is by design — re-authentication via the persisted refresh token is handled transparently by `baseQueryWithReAuth`.

---

## Permission-Based UI Gating

UI elements that require specific permissions are hidden (not just disabled) for users who do not hold them. Two patterns are used:

### PermissionGate Component

Wraps any subtree that should only render if the user holds a given permission:

```tsx
<PermissionGate permission="users:write">
  <Button onClick={openCreateModal}>Create User</Button>
</PermissionGate>
```

```tsx
// src/shared/components/PermissionGate.tsx
export function PermissionGate({ permission, children }: Props) {
  const { hasPermission } = useAuth();
  if (!hasPermission(permission)) return null;
  return <>{children}</>;
}
```

### useAuth Hook

Exposes the current auth state and the `hasPermission` helper:

```typescript
// src/features/auth/hooks/useAuth.ts
export function useAuth() {
  const { user, permissions, isAuthenticated } = useAppSelector(selectAuth);

  const hasPermission = useCallback(
    (permission: string) => permissions.includes(permission),
    [permissions],
  );

  return { user, permissions, isAuthenticated, hasPermission };
}
```

### Route Guards

Protected routes use a `ProtectedRoute` component that redirects unauthenticated users to `/login` and can optionally enforce a permission:

```tsx
<Route
  path="/admin/users"
  element={
    <ProtectedRoute requiredPermission="users:read">
      <UsersPage />
    </ProtectedRoute>
  }
/>
```

---

## URL-Synced Filter State

List pages synchronize their filter and pagination state to the URL query string. This means filters survive a page refresh and can be shared via URL.

### Pattern

The `useUrlParams` utility provides a typed interface for reading and writing URL search parameters. Each list page or feature hook uses it to derive its query state:

```typescript
// src/features/users/hooks/useUserFilters.ts
export function useUserFilters() {
  const [params, setParams] = useUrlParams({
    page:     { type: 'number', default: 1 },
    pageSize: { type: 'number', default: 20 },
    search:   { type: 'string', default: '' },
    role:     { type: 'string', default: '' },
    isActive: { type: 'boolean', default: true },
  });

  const setFilter = useCallback(
    (key: string, value: unknown) => setParams({ [key]: value, page: 1 }),
    [setParams],
  );

  return { filters: params, setFilter };
}
```

The RTK Query hook for the list receives the filter object directly, and RTK Query uses the serialized params as the cache key — a different filter combination is a different cache entry.

```tsx
// In UsersPage.tsx
const { filters, setFilter } = useUserFilters();
const { data, isFetching } = useListUsersQuery(filters);
```

### Benefits

- Filters survive a hard refresh.
- Sharing the URL shares the exact filtered view.
- The browser back button moves through filter states.
- No filter state is duplicated between Redux and the URL.

---

## AppLayout Shell

The `AppLayout` component is the outer shell that wraps all authenticated pages. It renders the sidebar, top navigation bar, and the main content outlet.

### Structure

```tsx
// src/shared/components/AppLayout.tsx
export function AppLayout() {
  return (
    <div className="flex h-screen">
      <Sidebar />
      <div className="flex flex-col flex-1 overflow-hidden">
        <Topbar />
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
```

### Permission-Aware Sidebar

The sidebar navigation items are declared with optional `permission` fields. Items are only rendered if the current user holds the required permission:

```typescript
const NAV_ITEMS: NavItem[] = [
  { label: 'Dashboard',   path: '/dashboard',    icon: HomeIcon },
  { label: 'Users',       path: '/admin/users',  icon: UsersIcon,  permission: 'users:read' },
  { label: 'Roles',       path: '/admin/roles',  icon: ShieldIcon, permission: 'roles:read' },
  { label: 'AI Query',    path: '/ai',           icon: SparkleIcon, permission: 'ai:query' },
  { label: 'Audit Log',   path: '/admin/audit',  icon: ClockIcon,  permission: 'audit:read' },
];
```

```tsx
// Inside Sidebar.tsx
{NAV_ITEMS.filter(item => !item.permission || hasPermission(item.permission)).map(item => (
  <NavLink key={item.path} to={item.path}>
    <item.icon />
    {item.label}
  </NavLink>
))}
```

An EMPLOYEE user who does not hold `users:read` will never see the Users nav item. The route guard provides a second layer of protection for direct URL access.
