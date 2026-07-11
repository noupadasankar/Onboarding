# features

## Purpose
This directory contains every feature of the OptiAgent application, organized as independent vertical slices. Each sub-folder is a self-contained module that owns the complete implementation of one product capability: its API calls, Redux state, React components, page-level views, custom hooks, TypeScript types, and validation schemas all live together under one feature name.

This approach — commonly called feature-first or vertical-slice architecture — keeps the code that changes together located together. A developer working on the `users` feature can navigate a single directory tree rather than hunting across a global `components/`, `redux/`, and `api/` folder. It also makes features easy to add, remove, or hand off independently.

## Responsibilities
- Host one sub-directory per product feature, each named after the domain concept it implements (e.g., `auth/`, `users/`, `dashboard/`).
- Allow each feature to own its full vertical slice: API layer, Redux slice, page components, shared-within-feature components, custom hooks, types, and validation.
- Serve as the only place where RTK Query endpoint definitions (`injectEndpoints`) are written for a given feature.

## Does NOT Contain
- Shared, cross-feature UI primitives (Button, Input, Dialog — these belong in `src/components/`).
- Global Redux store configuration or the RTK Query base API instance (those belong in `src/app/`).
- Application routing rules (route definitions belong in `src/router/`).
- Layout shells (AppLayout, Sidebar — those belong in `src/layouts/`).
- Global CSS or Tailwind configuration (those belong in `src/styles/`).

## Architecture Position
```
src/features/
  ├── auth/        ← login, auth state, token management
  ├── users/       ← user CRUD admin table
  ├── dashboard/   ← summary dashboard page
  └── <future>/    ← documents, AI chat, etc.

Each feature feeds upward into:
  src/router/      ← imports page components from features/*/pages/
  src/app/store    ← imports Redux slices from features/*/redux/
```

## Expected Contents
| Sub-directory | Status | Description |
|---|---|---|
| `auth/` | Implemented | Login form, `useAuth` hook, `authSlice`, `authApi`. |
| `users/` | Implemented | User CRUD table, `usersApi`, `rolesApi`, URL-synced filters. |
| `dashboard/` | Implemented | Summary dashboard page with high-level metrics. |
| `documents/` | Planned for Increment 3 | Document upload, listing, and metadata management. |
| `ai-chat/` | Planned for Increment 4 | Conversational AI interface backed by the Python AI service. |

### Standard sub-directory structure within each feature
```
features/<feature-name>/
  api/          RTK Query endpoint definitions (injectEndpoints on baseApi)
  components/   Feature-specific React components (not used by other features)
  hooks/        Custom hooks that compose API calls and local state for this feature
  pages/        Page-level components registered as route targets in src/router/
  redux/        Redux slice (actions, reducers, selectors)
  types/        TypeScript interfaces and type aliases for this feature's domain
  validation/   Zod schemas for forms and API response shapes
```
Not every feature requires every sub-directory; only the ones relevant to its scope are created.

## Design Principles
- **Single Responsibility** — each feature directory owns exactly one product capability.
- **Separation of Concerns** — API logic stays in `api/`, UI in `components/`, state in `redux/`; layers do not bleed into each other within a feature.
- **No Business Logic in components** — components call hooks; business rules live in hooks or the Redux slice.

## Current Status
Partially Implemented — `auth`, `users`, and `dashboard` are implemented. Future features (`documents`, `ai-chat`) are reserved for later increments.

## Future Work
- **Increment 3**: Add `documents/` feature for document management.
- **Increment 4**: Add `ai-chat/` feature for the conversational AI interface.
