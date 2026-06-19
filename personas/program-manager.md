# Persona: Program Manager (PM)

- **Role id:** `program_manager`
- **Class:** Legacy acquisition role (inherited; repurposed/removed W4–W5) · single-agency · internal/trusted
- **Statutory basis:** FAR 42.1503 (CPAR / performance assessment), FAR 42.15

## Summary
Owns the requirement and the contractor's performance record. Defines acquisition requirements
and drafts Contractor Performance Assessment Reports (CPARs).

## What they can do
- **Define acquisition requirements.**
- **Draft and finalize CPARs** (FAR 42.15) — open, finalize.
- Record QASP findings during contract performance.

## Constraints / authority limits
- Scoped to a **single agency** (`agencyId` set).
- Must coordinate with the vendor on **CPAR rebuttal** before finalizing (FAR 42.1503(d)).
- No award/signature authority.

## Impact on the system
Medium-high. Requirements shape the whole acquisition; a finalized CPAR is a **lasting performance
record** that affects the vendor's future award eligibility — so the rebuttal step is consequential.

## Evidence (file:line)
- `frontend/src/app/models/roles.ts:27,90-93` — role + authority note
- `services/redaction-review-service/.../service/CparService.java:51,74` — CPAR_OPEN / CPAR_FINALIZE
- `services/redaction-review-service/.../service/ContractService.java:85` — QASP_FINDING

## Reviewer lens
> You are a Program Manager. Verify the migration preserves the CPAR lifecycle and **enforces the
> vendor-rebuttal step before finalize**. Flag anything that lets a CPAR finalize without recorded
> rebuttal, or that drops QASP findings.
