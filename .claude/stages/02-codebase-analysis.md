# Stage 2 — Codebase Analysis

## Goal
Produce a complete inventory of the Angular frontend so nothing is missed during migration.

## Inventory Checklist

### Structure
- [ ] List all Angular modules (`NgModule`)
- [ ] List all components and their nesting depth
- [ ] List all services and their injection scope (root vs. module)
- [ ] List all routes and lazy-loaded chunks

### State Management
- [ ] Identify state approach (NgRx, BehaviorSubject, component-local, etc.)
- [ ] Document store shape if NgRx is used

### External Dependencies
- [ ] Angular Material / CDK components in use
- [ ] Third-party Angular-specific libraries with no React equivalent
- [ ] REST / GraphQL calls — which services own them

### Patterns to Flag
- [ ] Two-way binding (`[(ngModel)]`) — needs explicit React equivalent
- [ ] Content projection (`<ng-content>`) — maps to `children` / render props
- [ ] Lifecycle hooks used (`OnInit`, `OnDestroy`, etc.)
- [ ] Angular animations

## Outputs
- Component inventory table (name, route, dependencies, complexity score)
- Risk list: components that will be hardest to port
