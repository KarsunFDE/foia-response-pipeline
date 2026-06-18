# Stage 4 — Scope Selection

## Goal
Decide which components/routes migrate in which order to maximize value and minimize risk.

## Prioritization Criteria

| Factor | Weight |
|--------|--------|
| User-facing impact (high traffic routes first) | High |
| Angular complexity (simpler components first to build React muscle) | Medium |
| Shared dependencies (migrate leaf nodes before containers) | High |
| Team ownership (who can review the React output?) | Medium |

## Migration Wave Planning

### Wave 1 — Foundation (shared components, no business logic)
- [ ] Component: ___
- [ ] Component: ___

### Wave 2 — Feature routes (low complexity)
- [ ] Route: ___
- [ ] Route: ___

### Wave 3 — Feature routes (high complexity / state-heavy)
- [ ] Route: ___
- [ ] Route: ___

### Wave 4 — Shell / app-level concerns
- [ ] Auth guards / interceptors
- [ ] Layout components
- [ ] App bootstrapping

## Out of Scope (this iteration)
- List anything explicitly deferred and why.

## Outputs
- Ordered migration backlog linked to stage 5 specs
- "Do not touch yet" list to prevent scope creep during implementation
