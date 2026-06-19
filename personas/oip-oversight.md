# Persona: OIP / DOJ Oversight

- **Role id:** `oip_oversight`
- **Class:** Active FOIA role · **cross-tenant, read-only** · no agency affiliation (`agencyId: null`)
- **Statutory basis:** FOIA Improvement Act of 2016 (compliance reporting)

## Summary
Department-of-Justice Office of Information Policy oversight. Reads across all agencies to produce
government-wide FOIA compliance reporting. No operational authority.

## What they can do
- **Read-only** access across all agencies (cross-tenant).
- Produce **FOIA Improvement Act** compliance reports.

## Constraints / authority limits
- **No write/modify** authority anywhere.
- Cross-tenant read (`agencyId: null`) — sees every agency but changes nothing.
- Distinct from OIG: OIP is policy/compliance reporting, not investigative findings.

## Impact on the system
Low operationally — observe/report only. But the cross-tenant read scope is a sensitive data
surface: it must remain strictly read-only and must not become a write path during migration.

## Evidence (file:line)
- `frontend/src/app/models/roles.ts:23,71-75` — role + cross-tenant read-only authority note

## Reviewer lens
> You are OIP Oversight. Verify the migration preserves cross-tenant **read-only** access for
> compliance reporting and never grants this role a write/modify capability. Flag any control that
> would let oversight mutate agency data.
