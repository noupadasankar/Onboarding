# features/users

## Purpose
This feature provides the administrative user management capability of OptiAgent. It allows authorized administrators to view, create, edit, and deactivate user accounts through a paginated, filterable data table. All write operations (create, edit, deactivate) are gated by the `USERS_WRITE` permission; users without that permission see the table in read-only mode.

The feature treats the URL as the source of truth for filter and pagination state, enabling bookmarkable and shareable filtered views without additional client-side state management.

## Responsibilities
- Render `UserListPage` as the primary page, containing `UserFilters`, `UserTable`, and action entry points.
- Display users in `UserTable` with per-row action menus (edit, deactivate); action items are conditionally rendered based on `hasPermission('USERS_WRITE')`.
- Provide `UserFilters` for searching and filtering the user list; filter values are synced to URL query parameters via `useSearchParams`.
- Open `UserFormModal` (unified create/edit modal) when an admin clicks "Add User" or the edit action on a row.
- Show `DeactivateConfirmDialog` when an admin selects the deactivate action, requiring explicit confirmation before the API call is made.
- Fetch user data via `usersApi` (RTK Query) and role options via `rolesApi` (RTK Query), both injected into `baseApi`.
- Encapsulate all filter state management and derived query parameters inside the `useUsers` hook.

## Does NOT Contain
- Authentication logic or session state (belongs in `features/auth/`).
- Role-based access control — the action menu visibility is controlled by the `USERS_WRITE` permission string, never by role names.
- Shared UI primitives (Button, Input, Select, Dialog — imported from `src/components/ui/`).
- Global Redux store configuration (belongs in `src/app/`).

## Architecture Position
```
UserListPage
  ├── UserFilters          ← reads/writes URL query params (useSearchParams)
  ├── UserTable
  │     └── [per row] action menu  ← visible only if hasPermission('USERS_WRITE')
  │           ├── Edit → UserFormModal (edit mode)
  │           └── Deactivate → DeactivateConfirmDialog
  └── "Add User" button → UserFormModal (create mode)

useUsers hook
  └── reads URL params → builds RTK Query args → calls usersApi.useGetUsersQuery()

usersApi  (RTK Query, injected into baseApi)
  └── GET  /api/users          (list, paginated + filtered)
  └── POST /api/users          (create)
  └── PUT  /api/users/:id      (edit)
  └── POST /api/users/:id/deactivate

rolesApi  (RTK Query, injected into baseApi)
  └── GET  /api/roles          (options for role select in UserFormModal)
```

## Expected Contents
| Path | Description |
|---|---|
| `api/usersApi.ts` | RTK Query endpoint definitions for user CRUD operations. Provides tag-based cache invalidation so the list refetches after mutations. |
| `api/rolesApi.ts` | RTK Query endpoint definitions for fetching available roles, used to populate the role dropdown in `UserFormModal`. |
| `components/UserTable.tsx` | Data table rendering user rows with sortable columns and a per-row action menu gated by `USERS_WRITE`. |
| `components/UserFilters.tsx` | Search input and filter controls. Reads initial values from `useSearchParams` and writes changes back to the URL. |
| `components/UserFormModal.tsx` | Unified create/edit modal using React Hook Form + Zod. Submits to the appropriate `usersApi` mutation depending on mode. |
| `components/DeactivateConfirmDialog.tsx` | Confirmation dialog that requires the admin to explicitly confirm before the deactivate API call is dispatched. |
| `hooks/useUsers.ts` | Reads URL query params, derives RTK Query argument objects, and calls `useGetUsersQuery`. Returns data, loading state, and URL-updating filter handlers. |
| `pages/UserListPage.tsx` | Top-level page component that composes the above components and hooks into the full user management view. |
| `types/users.types.ts` | TypeScript interfaces: `User`, `UserFilters`, `CreateUserRequest`, `UpdateUserRequest`, `Role`. |
| `validation/userSchema.ts` | Zod schemas for the create and edit forms, including field constraints for name, email, and role assignment. |

## Design Principles
- **Single Responsibility** — each component has one job; `UserTable` renders, `useUsers` manages query state, `usersApi` owns the HTTP layer.
- **Separation of Concerns** — URL state management is isolated in `useUsers`; it does not leak into components.
- **No Business Logic in components** — permission checks and filter derivations are handled in hooks, not inside JSX.
- **No HTTP Logic in components** — components call RTK Query hooks; they never call `fetch` or Axios directly.

## Current Status
Implemented

## Future Work
- Bulk operations (bulk deactivate, bulk role reassignment) are planned for Increment 3.
- Export to CSV functionality is planned for Increment 3.
