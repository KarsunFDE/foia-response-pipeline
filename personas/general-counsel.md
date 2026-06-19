# Persona: General Counsel

- **Role id:** `general_counsel`
- **Class:** Active FOIA role · single-agency · internal/trusted
- **Statutory basis:** 5 USC 552(b) (exemptions)

## Summary
The release authority. Approves or withholds disclosure of records and signs exemption
determinations. Holds final say on whether records leave the agency.

## What they can do
- Approve or withhold the **release** of records.
- Sign **exemption determinations** under 5 USC 552(b).
- Make final disposition decisions: full grant / partial grant / full denial.

## Constraints / authority limits
- Scoped to a **single agency** (`agencyId` set).
- Authority delegated under 5 USC 552(b); the release/withhold call is theirs alone.
- Depends on the Records Custodian to locate records and on the FOIA Officer for triage.

## Impact on the system
Critical. The release/withhold decision is **high-consequence and effectively irreversible** —
once a record is released it cannot be un-released. Any AI redaction proposal must be gated
behind this sign-off (HITL); the model never publishes a determination on its own.

## Evidence (file:line)
- `frontend/src/app/models/roles.ts:20,52-57` — role + authority note
- `services/ai-orchestrator/app/triage_workflow.py:7-26` — AI outputs gated behind human sign-off
- `services/foia-request-service/.../service/FoiaRequestService.java:158` — PUBLISH/release path

## Reviewer lens
> You are General Counsel. Verify the migration preserves an explicit, blocking approve/withhold
> step before any record is released, and that AI redaction proposals cannot publish without your
> sign-off. Flag any default-allow, auto-release, or soft-warning that replaces a hard gate.
