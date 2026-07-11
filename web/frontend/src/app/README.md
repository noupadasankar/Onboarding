# app

## Purpose
This directory is the global application shell for the OptiAgent frontend. It owns the Redux store configuration, the typed dispatch and selector hooks used throughout the codebase, and the RTK Query base API instance from which all feature-level API slices are injected. Nothing here is tied to any single feature; it provides the foundation that every feature depends on.

By centralising the store and base API in one place, all feature slices share a single Redux context and a single Axios/fetch configuration (base URL, auth headers, token refresh logic) without duplicating setup code.

## Responsibilities
- Configure and export the Redux `store` (`store.ts`), including middleware registration for RTK Query.
- Export typed `useAppDispatch` and `useAppSelector` hooks (`hooks.ts`) so components never import untyped Redux hooks directly.
- Define the RTK Query `baseApi` instance (`api/baseApi.ts`): base URL, default headers, token injection, automatic token-refresh on 401, and the shared tag type registry used for cache invalidation across features.
- Re-export the `RootState` and `AppDispatch` TypeScript types consumed across the application.

## Does NOT Contain
- Feature-specific Redux slices (e.g., `authSlice`, `usersSlice` — these live in their respective `features/` sub-directories).
- UI components of any kind.
- Business logic, validation schemas, or domain types.
- Hardcoded API endpoint strings (individual endpoint definitions belong in each feature's `api/` sub-folder, injected into `baseApi`).

## Architecture Position
```
main.tsx
  └── <Redux Provider store={store}>   ← store.ts (this directory)
        └── App.tsx
              └── features/*
                    └── feature api slices  (injected into baseApi.ts)
                          └── baseApi.ts    ← single RTK Query client
```
`store.ts` is composed once at startup and provided to the entire component tree. `baseApi.ts` is the shared RTK Query client; feature slices call `baseApi.injectEndpoints()` to register their own endpoints without creating a second fetch client.

## Expected Contents
| Path | Description |
|---|---|
| `store.ts` | Configures the Redux store with `configureStore`. Registers RTK Query middleware. Exports `store`, `RootState`, and `AppDispatch`. |
| `hooks.ts` | Exports `useAppDispatch` and `useAppSelector` typed to `AppDispatch` and `RootState`. |
| `api/baseApi.ts` | Creates the RTK Query `createApi` instance with `fetchBaseQuery`. Handles base URL, Bearer token injection from Redux auth state, and 401 token-refresh logic. Exports the base query and the empty API object that features extend. |

## Design Principles
- **Single Responsibility** — this directory does one thing: provide the global Redux and RTK Query infrastructure.
- **Separation of Concerns** — store configuration is isolated from feature logic; features depend on this layer, not the reverse.
- **No Business Logic** — no domain rules, no field validation, no response transformation beyond generic error handling.
- **No HTTP Logic** — individual API calls are defined by features; this directory only configures the shared fetch client.

## Current Status
Implemented

## Future Work
No structural changes anticipated. If request-level middleware (e.g., logging, analytics) is added, it will be registered here in `store.ts`. No additional work planned at this layer beyond incremental tag-type additions to `baseApi.ts` as new features are introduced.
