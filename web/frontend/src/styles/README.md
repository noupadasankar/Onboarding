# styles

## Purpose
This directory contains the global CSS entry point for the OptiAgent frontend. Its sole file, `index.css`, is imported once in `main.tsx` and applies application-wide base styles, Tailwind CSS directives, and any CSS custom properties (design tokens) that must be available at the document root level.

Everything in this directory is truly global — it affects the entire application. Styles that are specific to a single feature, component, or layout belong co-located with that code (as Tailwind utility classes in JSX), not here.

## Responsibilities
- Declare the three Tailwind CSS directives (`@tailwind base`, `@tailwind components`, `@tailwind utilities`) that instruct the Tailwind compiler to inject its generated styles.
- Define CSS custom properties (e.g., `--color-primary`, `--radius`, `--font-sans`) on `:root` that establish design tokens consumed by Tailwind's theme configuration or directly in component markup.
- Apply any minimal global resets or base element styles that Tailwind's `preflight` does not already cover.

## Does NOT Contain
- Feature-specific styles — styles for a particular feature's components belong as Tailwind utility classes in that feature's JSX or, if unavoidable, in a CSS file co-located within `features/<name>/`.
- Component-level style overrides — components in `src/components/ui/` use CVA and Tailwind utilities, not global CSS rules.
- Animation keyframe definitions for individual components (these belong co-located with the component that uses them, or in a shared `lib/` utility if reused).
- Anything that imports or depends on JavaScript or TypeScript (this directory is pure CSS).

## Architecture Position
```
main.tsx
  └── import './styles/index.css'   ← loaded once, globally

index.css
  ├── @tailwind base            → Tailwind preflight + base element resets
  ├── @tailwind components      → Tailwind component utilities
  ├── @tailwind utilities       → all generated utility classes
  └── :root { --css-vars }     → design tokens available everywhere
```
`index.css` is the single seam between the CSS world and the Tailwind build pipeline. Vite processes it via the PostCSS / Tailwind plugin configured in `tailwind.config.ts`.

## Expected Contents
| File | Description |
|---|---|
| `index.css` | The global stylesheet. Contains Tailwind directives and root-level CSS custom properties. Imported by `main.tsx`. |

## Design Principles
- **Single Responsibility** — this directory has exactly one concern: global CSS scaffolding.
- **Separation of Concerns** — global styles are isolated from component styles; the boundary is enforced by convention (Tailwind utilities in JSX, global tokens here).
- **Pure Functions** — CSS custom properties on `:root` are declarative and have no side effects.

## Current Status
Implemented

## Future Work
No additional work planned at this layer. If a design token system (e.g., a light/dark theme toggle) is introduced, the additional custom property sets will be added to `index.css` here.
