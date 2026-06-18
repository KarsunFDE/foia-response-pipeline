# Stage 3 — Target State Configuration

## Goal
Lock in the React stack decisions before any code is written so stage 5 specs don't drift.

## Decisions to Lock

### Tooling
- Bundler: Vite / CRA / Next.js?
- Language: TypeScript (assumed) — strict mode on/off?
- Linter / formatter: ESLint + Prettier config?

### Component Library
- Replacement for Angular Material: MUI / shadcn/ui / Tailwind-only?
- Icon set?

### Routing
- React Router v6 — loader/action pattern or classic?
- Route structure — mirrors Angular routes 1:1 or redesigned?

### State Management
- Server state: React Query / SWR?
- Client/global state: Zustand / Redux Toolkit / Context?

### API Layer
- Axios instance config, base URL, auth interceptors
- Where do service calls live? (custom hooks, React Query query fns, etc.)

### Testing
- Unit: Vitest / Jest?
- Component: React Testing Library?
- E2E: Playwright / Cypress?

### Folder Convention
```
src/
  components/   # shared / design-system
  features/     # one folder per route/feature
  hooks/
  services/
  store/
```

## Outputs
- ADR (Architecture Decision Record) entries for each locked decision
- Starter config files committed before any feature work begins
