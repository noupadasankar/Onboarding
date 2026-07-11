# components

## Purpose
This directory contains shared, domain-agnostic UI primitives used across the entire OptiAgent frontend. Every component here is a styling and interaction wrapper with no awareness of any business concept — it does not know what a "user", a "permission", or an "AI agent" is. Components here accept generic props (labels, variants, event handlers, children) and render consistently styled HTML elements.

By centralising primitives here, every feature in `src/features/` imports from a single source of truth, ensuring visual consistency without duplicating Tailwind utility combinations or CVA variant definitions.

## Responsibilities
- Provide low-level UI building blocks: buttons, inputs, labels, cards, badges, selects, dialogs, and similar primitives.
- Implement visual variants using CVA (`class-variance-authority`) so components can be used in different sizes, colours, or states without prop drilling or conditional class strings scattered across the codebase.
- Expose clean, well-typed prop interfaces that features and layouts can depend on.
- Ensure accessibility-compliant markup (correct ARIA attributes, semantic HTML, keyboard navigation) at the primitive level so features inherit it automatically.

## Does NOT Contain
- Any reference to business domain concepts (users, auth, permissions, documents, AI responses).
- API calls, Redux state, or data fetching of any kind.
- Feature-specific composite components (e.g., `UserTable`, `LoginForm` — those live in their respective `features/<name>/components/` directories).
- Page-level layouts or navigation (those belong in `src/layouts/`).
- Global CSS (belongs in `src/styles/`).

## Architecture Position
```
src/components/ui/
  └── Button, Input, Label, Card, Badge, Select, Dialog, ...

Used by:
  ├── src/features/auth/components/LoginForm.tsx
  ├── src/features/users/components/UserFormModal.tsx
  ├── src/features/users/components/DeactivateConfirmDialog.tsx
  ├── src/layouts/Sidebar.tsx
  └── any other feature or layout that needs styled primitives
```
Components here have no upstream knowledge of who uses them; dependencies flow only downward (features depend on components, never the reverse).

## Expected Contents
| Path | Description |
|---|---|
| `ui/Button.tsx` | Clickable button with CVA variants for visual style (`default`, `destructive`, `outline`, `ghost`) and size (`sm`, `md`, `lg`). |
| `ui/Input.tsx` | Styled text input with forwarded ref support and error-state styling. |
| `ui/Label.tsx` | Form label with consistent typography and association to input elements via `htmlFor`. |
| `ui/Card.tsx` | Container component with border, shadow, and padding variants for content grouping. |
| `ui/Badge.tsx` | Inline status indicator with CVA colour variants (e.g., `active`, `inactive`, `pending`). |
| `ui/Select.tsx` | Styled single-select dropdown with option list support and disabled state. |
| `ui/Dialog.tsx` | Modal dialog with overlay, focus trap, and ESC-to-close behaviour. Used by `UserFormModal` and `DeactivateConfirmDialog`. |

## Design Principles
- **Single Responsibility** — each component renders one type of UI element and nothing else.
- **No Business Logic** — components accept and render props; they make no decisions about domain data.
- **No HTTP Logic** — components never call APIs or dispatch Redux actions.
- **Stateless** — components are stateless where possible; any internal state is limited to UI concerns (e.g., open/closed for a dropdown).
- **Pure Functions** — given the same props, a component always renders the same output.

## Current Status
Implemented

## Future Work
Additional primitives (e.g., `Tooltip`, `Skeleton`, `Table`, `Tabs`) will be added to `components/ui/` as new features require them in later increments. No structural changes to this directory are planned.
