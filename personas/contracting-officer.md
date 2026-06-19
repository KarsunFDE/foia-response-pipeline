# Persona: Contracting Officer (CO)

- **Role id:** `contracting_officer`
- **Class:** Legacy acquisition role (inherited; repurposed/removed W4–W5) · single-agency · internal/trusted
- **Statutory basis:** FAR 1.602-1 (authority), FAR 15.206 (amendments), FAR 43.102/43.103 (modifications)

## Summary
The only role with warranted authority to bind the government on a contract action. Signs awards,
issues amendments, terminates, and unseals proposals after the closing deadline. The strongest
hard-gate authority in the inherited acquisition model.

## What they can do
- **Sign** the award decision.
- **Issue amendments** (FAR 15.206).
- **Terminate** a contract.
- **Unseal** sealed proposals at/after the closing deadline.
- Answer vendor questions during Q&A; record the award decision.

## Constraints / authority limits
- Scoped to a **single agency** (`agencyId` set); identity/warrant enforcement lives downstream
  in the Java service, not the orchestrator.
- **Cannot score proposals** — source selection is delegated to evaluators/SSA (separation of duties).
- Time-gated: cannot view sealed proposals before `closingAt`.
- Only the CO executes a modification (reserved action; never auto-processed).

## Impact on the system
Critical. The award/amend/terminate and unseal actions are **irreversible, high-consequence**
events that bind funds and reveal sealed competitive material. Every such action is a high-value
audit event carrying actor identity, role, and package hash.

## Evidence (file:line)
- `frontend/src/app/models/roles.ts:25,78-81` — role + authority note
- `services/foia-request-service/.../model/Proposal.java:11-13` — CO unseals after closing
- `services/foia-request-service/.../service/AmendmentService.java:65` — AMEND
- `services/foia-request-service/.../service/QnaService.java:74` — QNA_ANSWER
- See also project `CLAUDE.md` (orchestrator gate logic + reserved-action policy)

## Reviewer lens
> You are a Contracting Officer. Verify no award/amend/terminate/unseal can execute without an
> explicit CO approve step, that sealed proposals stay sealed until `closingAt`, and that actor
> identity + package hash stay on the audit path. Default to REFUTE: if the plan does not prove
> the gate survives, assume it does not.
