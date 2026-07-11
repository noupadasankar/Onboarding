# src

## Purpose
This is the root source directory for the OptiAgent React frontend. All application code lives beneath this folder, organized into a set of purpose-specific top-level directories. The two entry-point files, `main.tsx` and `App.tsx`, live directly here: `main.tsx` bootstraps the React DOM and wraps the application in global providers (Redux store, React Router), while `App.tsx` defines the top-level component tree that connects the router to the layout shell.

Nothing in this directory is feature-specific. It is the structural backbone that ties together the feature modules, shared components, routing rules, global state, and styling into a single cohesive application.

## Responsibilities
- Host `main.tsx` (React DOM bootstrap, provider composition) and `App.tsx` (root component).
- Group application code into clearly scoped sub-directories: `app/`, `components/`, `features/`, `layouts/`, `lib/`, `router/`, and `styles/`.
- Serve as the import root for all absolute-path aliases configured in `tsconfig.json` / `vite.config.ts`.

## Does NOT Contain
- Feature-specific logic, components, or state (belongs in `features/<feature-name>/`).
- Business domain types or validation schemas (belongs inside the relevant feature).
- Inline styles or component-level CSS (belongs in `styles/` or co-located with the component via Tailwind utility classes).
- Test files at this level (tests are co-located with the code they exercise).

## Architecture Position
```
main.tsx
  └── <Providers>          (Redux Store, React Router BrowserRouter)
        └── App.tsx
              └── router/  (route definitions + ProtectedRoute)
                    └── layouts/AppLayout  (Sidebar + Outlet)
                          └── features/*/pages  (page-level components)
```
`main.tsx` is the single entry point compiled by Vite. Everything downstream is a tree of React components and Redux slices assembled here.

## Expected Contents
| Path | Description |
|---|---|
| `main.tsx` | Vite/React entry point. Mounts `<App />` inside Redux `<Provider>` and `<BrowserRouter>`. |
| `App.tsx` | Root component. Renders `<RouterProvider>` or top-level `<Routes>`. |
| `app/` | Redux store, typed hooks, RTK Query base API. See `app/README.md`. |
| `components/` | Shared, domain-agnostic UI primitives (Button, Input, Dialog, etc.). See `components/README.md`. |
| `features/` | Feature vertical slices (auth, users, dashboard, and future features). See `features/README.md`. |
| `layouts/` | Application shell layouts (AppLayout, Sidebar). See `layouts/README.md`. |
| `lib/` | Utility helpers and third-party configuration that do not belong to a single feature (planned for future increments). |
| `router/` | React Router v6 route definitions and ProtectedRoute. See `router/README.md`. |
| `styles/` | Global CSS entry point with Tailwind directives. See `styles/README.md`. |

## Design Principles
- **Separation of Concerns** — each sub-directory has a single, well-defined role; no directory bleeds into another's responsibility.
- **Single Responsibility** — `main.tsx` only bootstraps; `App.tsx` only composes the top-level tree; routing, state, and UI are each delegated to their own directory.

## Current Status
Implemented

## Future Work
`lib/` will be populated with shared utilities (date formatting, error serialization, analytics helpers) as additional features are introduced in later increments. No structural changes to the top-level layout of `src/` are anticipated.
