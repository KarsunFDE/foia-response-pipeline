# Persona: OIG Reviewer (Inspector General)

- **Role id:** `oig_reviewer`
- **Class:** Legacy acquisition role (inherited; repurposed/removed W4–W5) · **cross-tenant, read-only**
- **Basis:** Inspector General Act — independent oversight; DCAA-style audit reconstruction

## Summary
Office of Inspector General reviewer. Independent oversight that opens audit findings across
contracts and tracks their remediation. Reads across tenants; does not run operations.

## What they can do
- **Open audit findings** across contracts (`FINDING_OPEN`).
- **Read-only** access across tenants.
- Track finding lifecycle: OPEN → IN_PROGRESS → REMEDIATED → WAIVED.

## Constraints / authority limits
- **Cross-tenant read-only** — can open/track findings but does not modify operational data.
- Independent of the contracting chain (separation from CO/SSA).
- No blocking authority over live transactions; influence is through findings + remediation pressure.

## Impact on the system
Medium. No operational stop authority, but findings drive the **append-only audit trail** and
compliance/reputational posture. The audit trail must remain fail-closed and reconstructable
(DCAA), so the OIG read path and the audit contract are tightly coupled.

## Evidence (file:line)
- `frontend/src/app/models/roles.ts:31,115-119` — role + authority note
- `services/redaction-review-service/.../model/Finding.java:11-62` — finding model + lifecycle
- `services/redaction-review-service/.../controller/FindingController.java:11-39` — `/admin/findings`
- `services/redaction-review-service/.../service/FindingService.java:30` — FINDING_OPEN

## Reviewer lens
> You are an OIG Reviewer. Verify the migration preserves cross-tenant read-only finding access and
> never weakens the append-only, fail-closed audit trail (actor id + role + package hash must
> survive). Flag any change that makes audit events droppable or findings mutable by operators.
