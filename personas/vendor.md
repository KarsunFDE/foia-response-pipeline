# Persona: Vendor / Contractor

- **Role id:** `vendor`
- **Class:** Legacy acquisition role (inherited; repurposed/removed W4–W5) · **external** · multi-agency visibility (`agencyId: null`)
- **Statutory basis:** FAR 15 (proposals), FAR 15.206 (amendments), FAR 42.1503(d) (CPAR rebuttal), FAR 15.506 (debrief)

## Summary
The company competing for or holding a contract, identified by DUNS/UEI/CAGE. External party with
visibility to the agencies it does business with, but walled off from other vendors' data.

## What they can do
- **Submit proposals** (Volumes I/II/III per Section M).
- **Acknowledge amendments** (FAR 15.206).
- File a **CPAR rebuttal** (FAR 42.1503(d)).
- Answer questions during the **Q&A** period.
- **Request a debrief** after an unsuccessful award (FAR 15.506 — 5-day window).

## Constraints / authority limits
- **External** (`agencyId: null`); cannot access other vendors' data.
- **Multi-tenant visibility** via an `agencyVisibility` list (SAM.gov-style), but scoped per agency.
- Sealed-proposal access control: own proposal visible only after CO unseal or post-award.
- Subject to NAICS/set-aside classification.

## Impact on the system
High. Proposal content drives the competition; a CPAR rebuttal shapes the lasting performance
record; a debrief request can trigger a **protest**. As an external party it is part of the
inverted threat model — its inputs are an attack surface.

## Evidence (file:line)
- `frontend/src/app/models/roles.ts:30,108-112` — role + DUNS + authority note
- `services/foia-request-service/.../model/Vendor.java:20-56` — DUNS/UEI/CAGE/agencyVisibility
- `services/foia-request-service/.../model/Proposal.java:19-58` — sealed until CO unseal
- `services/foia-request-service/.../service/ProposalService.java:61,80` — PROPOSAL_SUBMIT / PROPOSAL_ACK_AMEND
- `services/redaction-review-service/.../service/CparService.java:62` — CPAR_REBUTTAL
- `services/redaction-review-service/.../service/AwardService.java:84` — DEBRIEF_REQ

## Reviewer lens
> You are a Vendor (external, untrusted). Verify the migration keeps vendor access scoped to its
> own data and visible agencies, that proposals stay sealed until unseal/award, and that
> rebuttal/debrief windows are enforced. Flag any cross-vendor data leak or premature proposal exposure.
