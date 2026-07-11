# layouts

## Purpose
This directory contains the application shell layouts that frame all authenticated pages in OptiAgent. Layouts are structural scaffolds — they define how the screen is divided into regions (sidebar, main content area) and how navigation is presented, but they contain no feature-specific business logic.

By isolating layout concerns here, every authenticated route inherits a consistent frame without duplicating structural markup across page components. Feature pages only need to render their own content; the surrounding chrome is provided automatically through React Router's `<Outlet>` mechanism.

## Responsibilities
- Provide `AppLayout.tsx`: a full-screen shell that renders a fixed sidebar on the left and a scrollable main content area on the right, using React Router's `<Outlet>` to inject the active page component.
- Provide `Sidebar.tsx`: the left-hand navigation panel containing the application logo, navigation links to each section (Dashboard, Users, etc.), the current user's display name, and a sign-out action.
- Gate navigation link visibility in `Sidebar.tsx` using permission checks via `useAuth().hasPermission()` — links a user does not have access to are not rendered. Role strings are never used for this purpose.
- Handle the sign-out action in `Sidebar.tsx` by dispatching the logout flow from `features/auth`.

## Does NOT Contain
- Feature-specific business logic or domain data (no user CRUD, no AI calls, no document handling).
- Route definitions — layouts are consumed by the router, not defined by it (`src/router/` owns route configuration).
- Public-facing layouts such as the login page — the login page manages its own centred layout without `AppLayout`.
- Page-level components — individual pages live in their respective `features/<name>/pages/` directories.

## Architecture Position
```
React Router route tree (src/router/)
  └── <ProtectedRoute>          ← enforces isAuthenticated
        └── <AppLayout>         ← this directory
              ├── <Sidebar>     ← permission-gated nav links, user info, sign-out
              └── <Outlet>      ← renders the matched child route's page component
                    ├── /dashboard  → DashboardPage (features/dashboard)
                    └── /users      → UserListPage  (features/users)
```
`AppLayout` itself renders once per navigation; only the `<Outlet>` subtree changes as the user moves between routes.

## Expected Contents
| Path | Description |
|---|---|
| `AppLayout.tsx` | Composes `<Sidebar>` and `<Outlet>` into a two-column flex/grid shell. Applies global authenticated-page viewport constraints. |
| `Sidebar.tsx` | Left navigation panel. Reads `useAuth()` for current user info and `hasPermission()` to conditionally render nav items. Dispatches logout on sign-out click. |

## Design Principles
- **Single Responsibility** — `AppLayout` structures the screen; `Sidebar` handles navigation; neither does anything else.
- **Separation of Concerns** — layout structure is fully decoupled from page content and from feature logic.
- **No Business Logic** — permission checks are delegated to `useAuth().hasPermission()`; layout components make no access-control decisions independently.
- **No HTTP Logic** — layouts do not make API calls. The sign-out action in `Sidebar.tsx` delegates to the auth feature's logout mutation.

## Current Status
Implemented

## Future Work
- A collapsible or responsive sidebar variant may be introduced in a future increment to support smaller viewport sizes.
- If a secondary layout is needed for a full-screen AI chat view, an additional layout component will be added here.
- No additional work planned at this layer for the current increment.
