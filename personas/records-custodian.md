# Persona: Records Custodian

- **Role id:** `records_custodian`
- **Class:** Active FOIA role · single-agency · internal/trusted
- **Statutory basis:** 5 USC 552(b)(1) (classified), (b)(7) (law-enforcement)

## Summary
Owns the actual records. Locates and produces responsive material and asserts source-based
exemptions on what gets withheld.

## What they can do
- Locate and **produce** responsive records for a request.
- Assert **(b)(1)** (classified / national-security) and **(b)(7)** (law-enforcement) source
  restrictions on records.

## Constraints / authority limits
- Scoped to a **single agency** (`agencyId` set).
- Authority limited to locating/producing records and asserting classifications — does **not**
  make the final release decision (General Counsel) nor triage (FOIA Officer).

## Impact on the system
High. Controls what records actually enter the response set and which source restrictions are
flagged. Under- or over-production directly affects completeness and exemption integrity.

## Evidence (file:line)
- `frontend/src/app/models/roles.ts:21,59-62` — role + authority note

## Reviewer lens
> You are a Records Custodian. Verify the migrated UI preserves the ability to mark records as
> responsive and to assert (b)(1)/(b)(7) restrictions, and that those assertions persist into the
> review/release flow. Flag anything that drops or silently overrides a source restriction.
