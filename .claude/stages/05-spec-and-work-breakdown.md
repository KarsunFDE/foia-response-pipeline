# Stage 5 — Spec and Work Breakdown

## Goal
Produce a per-component spec fine-grained enough that a developer (or agent) can implement without ambiguity.

## Spec Template

Repeat this block for each item from stage 4's migration backlog.

---

### [Component / Route Name]

**Angular source:** `path/to/component.ts`

**React target:** `src/features/.../ComponentName.tsx`

**Props interface:**
```ts
interface ComponentNameProps {
  // ...
}
```

**State:**
- Local state: ___
- Server state (React Query key + endpoint): ___
- Global store slice (if any): ___

**Side effects / lifecycle equivalents:**
- `ngOnInit` → `useEffect(fn, [])`
- `ngOnDestroy` → cleanup return in same `useEffect`

**Angular patterns to translate:**
- [ ] `[(ngModel)]` on field X → controlled input with `useState`
- [ ] `*ngIf` on Y → conditional render `{condition && <Y />}`
- [ ] `*ngFor` on Z → `.map()`

**Acceptance criteria:**
- [ ] Renders without console errors
- [ ] All existing E2E paths pass
- [ ] RTL unit test for primary interaction

---

## Work Breakdown Summary

| # | Item | Complexity | Assignee | Status |
|---|------|-----------|----------|--------|
| 1 | | S/M/L | | Todo |
| 2 | | | | |

## Outputs
- One filled spec block per component in scope
- Work breakdown table ready to feed stage 6
