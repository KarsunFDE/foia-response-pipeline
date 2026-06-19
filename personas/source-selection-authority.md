# Persona: Source Selection Authority (SSA)

- **Role id:** `ssa`
- **Class:** Legacy acquisition role (inherited; repurposed/removed W4–W5) · single-agency · internal/trusted
- **Statutory basis:** FAR 15.303(b)(6) (final award decision)

## Summary
Makes the final source-selection decision and signs the Source Selection Decision Document (SSDD).
The terminal authority in a competitive award.

## What they can do
- Make the **final award decision**.
- **Sign the SSDD** and authorize contract award.

## Constraints / authority limits
- Scoped to a **single agency** (`agencyId` set).
- Bound by the **consensus scores** from the evaluation panel — decides on the record, not by
  re-scoring.
- The AI orchestrator may **draft** an SSDD, but it is non-authoritative and requires SSA approval.

## Impact on the system
Critical. The award decision is **irreversible** and triggers vendor debrief/protest windows.
Any AI-drafted SSDD must remain a draft until the SSA signs.

## Evidence (file:line)
- `frontend/src/app/models/roles.ts:28,96-99` — role + authority note
- `services/redaction-review-service/.../service/AwardService.java:62` — AWARD
- `services/redaction-review-service/.../service/RedactionReviewService.java:135` — SSDD_DRAFT (AI → SSA approval)

## Reviewer lens
> You are the Source Selection Authority. Verify no award executes without an explicit SSA sign
> step, that AI-drafted SSDDs cannot self-promote to final, and that the decision binds to the
> consensus record. Flag any auto-award or default-allow.
