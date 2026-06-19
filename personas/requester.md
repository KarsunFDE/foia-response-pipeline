# Persona: Requester (External)

- **Role id:** `requester`
- **Class:** Active FOIA role · **external / untrusted** · no agency affiliation (`agencyId: null`)
- **Statutory basis:** 5 USC 552(a)(6)(A)(i) (submit), 5 USC 552(a)(6)(E) (expedited)

## Summary
The member of the public (journalist, citizen, commercial party) who files a FOIA request.
**The FOIA threat model is inverted** — the requester is treated as a potentially adversarial,
external party. Authority is read-only and externally scoped.

## What they can do
- **Submit** FOIA requests.
- **Track** request status.
- File **appeals**.
- Request **expedited processing** and **fee waivers**.

## Constraints / authority limits
- **External / untrusted** — read-only beyond their own submission; no agency affiliation.
- Cannot see internal pipeline state, other requesters' data, or agency-internal records.
- Fee treatment driven by `requesterType` (commercial / news-media-educational-scientific / other).

## Impact on the system
External-facing entry point. Triggers intake and defines the scope of disclosure. Because the
model treats this party as adversarial, every requester-supplied input is an attack surface —
the inverted threat model must survive the migration (no privilege creep).

## Evidence (file:line)
- `frontend/src/app/models/roles.ts:5-7,22,65-68` — inverted threat model + authority note
- `services/foia-request-service/.../model/FoiaRequest.java:16-17,59-63` — requester as external/adversarial

## Reviewer lens
> You are the FOIA security reviewer modeling the Requester as adversarial. Verify the migration
> keeps requester authority read-only and externally scoped — no access to internal pipeline
> state or other tenants. Flag any new field, route, or default that grants a requester more than
> submit/track/appeal.
