# features/auth

## Purpose
This feature owns everything related to authentication in the OptiAgent frontend. It handles the login flow, persists the authenticated session in Redux, exposes a `useAuth` hook for permission-gated access throughout the application, and coordinates logout by calling the API before clearing local state.

Authentication state is the foundation on which all other features depend. Centralising it here ensures that token management, permission checks, and session teardown follow a single, consistent pattern across the application.

## Responsibilities
- Render the `LoginPage` and `LoginForm` components for unauthenticated users.
- Call the authentication API endpoints (`/auth/login`, `/auth/logout`, `/auth/me`) via `authApi` (RTK Query injected into `baseApi`).
- Store `user`, `accessToken`, `refreshToken`, and `permissions[]` in the `authSlice` Redux slice after a successful login.
- Export the `useAuth` hook, which provides the current user object, authentication status, and a `hasPermission(permissionKey)` helper used for permission-gated UI across all features.
- Execute logout in the correct order: call the logout API endpoint, then dispatch `clearAuth` to wipe Redux state (ensuring the server session is invalidated before the client forgets its credentials).

## Does NOT Contain
- Role-based access control checks — gating is always done via specific permission strings, never role names.
- Route protection logic — `ProtectedRoute` in `src/router/` enforces authentication at the routing layer.
- Shared UI primitives such as Button or Input — those are imported from `src/components/ui/`.
- User management (creating, editing, or deactivating users) — that belongs in `features/users/`.

## Architecture Position
```
POST /api/auth/login
  └── authApi (RTK Query)
        └── authSlice (Redux)
              ├── accessToken  → injected into baseApi headers by app/api/baseApi.ts
              ├── refreshToken → used by baseApi 401 refresh logic
              ├── user         → displayed in Sidebar, accessible via useAuth()
              └── permissions  → consumed by useAuth().hasPermission() everywhere

useAuth() hook
  └── reads authSlice state
  └── exposes: { user, isAuthenticated, hasPermission }
```

## Expected Contents
| Path | Description |
|---|---|
| `api/authApi.ts` | RTK Query endpoint definitions for `login`, `logout`, and `me` (current user fetch). Injected into `baseApi`. |
| `components/LoginForm.tsx` | Controlled form built with React Hook Form + Zod validation. Dispatches login via `authApi`. |
| `hooks/useAuth.ts` | Reads `authSlice` state; exposes `user`, `isAuthenticated`, and `hasPermission(key: string): boolean`. |
| `pages/LoginPage.tsx` | Public page that renders `LoginForm` inside a centred layout. Redirects to `/dashboard` when already authenticated. |
| `redux/authSlice.ts` | Redux slice managing `user`, `accessToken`, `refreshToken`, `permissions[]`. Exports `clearAuth` action used on logout. |
| `types/auth.types.ts` | TypeScript interfaces: `User`, `AuthState`, `LoginRequest`, `LoginResponse`, `Permission`. |
| `validation/loginSchema.ts` | Zod schema for the login form (`email` + `password` fields with constraints). |

## Design Principles
- **Single Responsibility** — this feature owns authentication and nothing else.
- **Separation of Concerns** — API calls live in `api/`, Redux state in `redux/`, UI in `components/` and `pages/`, reusable logic in `hooks/`.
- **No Business Logic in components** — `LoginForm` submits credentials; all token handling and state updates happen in `authApi` and `authSlice`.
- **Stateless validation** — Zod schemas in `validation/` are pure functions with no side effects.
- **Pure Functions** — `hasPermission` in `useAuth` is a pure derivation from the `permissions[]` array; it performs no API calls.

## Current Status
Implemented

## Future Work
- Token silent-refresh (automatic `accessToken` renewal using `refreshToken` without user interaction) may be added to `app/api/baseApi.ts` in a future increment if session longevity requirements increase.
- Multi-factor authentication support is planned for Increment 3.
