# router

## Purpose
This directory owns the complete React Router v6 route configuration for the OptiAgent frontend. It defines which URL paths map to which page components, how public and private routes are structured, and how authentication and permission requirements are enforced at the routing layer.

Centralising routing here means page components remain simple: they do not contain redirect logic or access-control conditionals. Those responsibilities are handled once, in this directory, for all routes.

## Responsibilities
- Define all application routes in `index.tsx` using React Router v6's `createBrowserRouter` or `<Routes>` / `<Route>` composition.
- Export the `ProtectedRoute` component, which redirects unauthenticated users to `/login` and, when a `permission` prop is supplied, redirects users who lack that permission to an appropriate fallback.
- Wrap all authenticated routes inside `AppLayout` (from `src/layouts/`) so the sidebar and navigation chrome are applied consistently.
- Register public routes (accessible without authentication, e.g., `/login`) separately from protected routes.
- Import page components from their respective `features/<name>/pages/` directories; the router is the only layer that couples feature pages to URLs.

## Does NOT Contain
- Page component implementations (those live in `features/<name>/pages/`).
- Layout component implementations (those live in `src/layouts/`).
- Authentication state management or token logic (those live in `features/auth/`).
- Navigation UI such as the sidebar or breadcrumbs (those live in `src/layouts/`).

## Architecture Position
```
main.tsx
  └── <RouterProvider router={router}>   ← router/index.tsx
        ├── /login                        Public route
        │     └── LoginPage (features/auth/pages)
        └── <ProtectedRoute>              Checks isAuthenticated
              └── <AppLayout>            (src/layouts/)
                    ├── /dashboard        <ProtectedRoute>
                    │     └── DashboardPage (features/dashboard/pages)
                    └── /users            <ProtectedRoute permission="USERS_READ">
                          └── UserListPage (features/users/pages)
```

## Expected Contents
| Path | Description |
|---|---|
| `index.tsx` | Defines the full route tree. Exports the configured router instance consumed by `main.tsx`. |
| `ProtectedRoute.tsx` | Wrapper component that reads `isAuthenticated` from `useAuth()`. Redirects to `/login` if not authenticated. Accepts an optional `permission` prop; if provided and the user lacks that permission, redirects to `/dashboard` or renders a 403 view. |

## Design Principles
- **Single Responsibility** — this directory owns URL-to-component mapping and access enforcement only.
- **Separation of Concerns** — routing logic is fully decoupled from feature logic; features expose pages, the router connects them to URLs.
- **No Business Logic** — `ProtectedRoute` checks a boolean (`isAuthenticated`) and an optional permission string; it does not evaluate domain rules.

## Current Status
Implemented

## Future Work
- New routes for `documents/` and `ai-chat/` features will be added here in Increments 3 and 4, respectively.
- If route-level code splitting (lazy loading via `React.lazy`) is introduced for performance, it will be applied in `index.tsx` at the route definition level.
