# Persona: Evaluator (TEP Member)

- **Role id:** `evaluator`
- **Class:** Legacy acquisition role (inherited; repurposed/removed W4–W5) · single-agency · internal/trusted
- **Statutory basis:** FAR 15.305 (proposal evaluation)

## Summary
Technical Evaluation Panel member. Scores assigned proposals against the Section M evaluation
factors and supplies narrative rationale. Feeds the consensus that the SSA decides on.

## What they can do
- **Score** assigned proposals against Section M factors (FAR 15.305).
- Provide **narrative rationale** for non-satisfactory ratings.
- Participate in **panel consensus** (per-factor, per-proposal scoring).

## Constraints / authority limits
- Scoped to a **single agency** (`agencyId` set).
- Must be **assigned to the panel** before scoring (`EVAL_PANEL_ASSIGN`).
- **Cannot modify other evaluators' scores**; no final award authority.

## Impact on the system
High. Scores roll up into the consensus that drives the SSA's award decision — they directly
influence who wins. Score integrity (assignment-gated, non-tamperable) is the key property.

## Evidence (file:line)
- `frontend/src/app/models/roles.ts:29,102-105` — role + authority note
- `frontend/src/app/components/evaluator-workspace/evaluator-workspace.component.ts:10-94` — scoring workspace
- `services/redaction-review-service/.../service/RedactionReviewService.java:60,73,96` — EVAL_CREATE / EVAL_PANEL_ASSIGN / EVAL_SCORE

## Reviewer lens
> You are a TEP Evaluator. Verify scoring is gated on panel assignment, that an evaluator cannot
> edit another's scores, and that narrative rationale persists. Flag any control that lets an
> unassigned user score or that allows cross-evaluator score edits.
