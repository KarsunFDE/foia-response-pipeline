# Persona: Contract Specialist (CS)

- **Role id:** `contract_specialist`
- **Class:** Legacy acquisition role (inherited; repurposed/removed W4–W5) · single-agency · internal/trusted
- **Statutory basis:** FAR 1.603 (limited delegated authority)

## Summary
The CO's drafting hand. Prepares solicitations and amendments but holds no signature authority —
a deliberate separation of duties from the CO/SSA.

## What they can do
- **Draft** solicitations / requests.
- **Prepare** amendments.
- Answer vendor questions during Q&A; publish/cancel solicitations.

## Constraints / authority limits
- Scoped to a **single agency** (`agencyId` set).
- **Cannot sign award** (FAR 1.603) — final signature is delegated to the SSA/CO.
- No independent scoring authority.

## Impact on the system
Medium. Shapes the solicitation and amendment content that everything downstream depends on, but
introduces no irreversible binding action on its own.

## Evidence (file:line)
- `frontend/src/app/models/roles.ts:26,84-87` — role + authority note
- `services/foia-request-service/.../service/FoiaRequestService.java:158,172` — PUBLISH/CANCEL
- `services/foia-request-service/.../service/AmendmentService.java:65` — AMEND

## Reviewer lens
> You are a Contract Specialist. Verify the migration preserves the draft/prepare flow **without**
> ever granting the CS a sign/award capability. Flag any control that lets a drafter finalize.
