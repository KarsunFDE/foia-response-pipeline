# Persona: FOIA Officer

- **Role id:** `foia_officer`
- **Class:** Active FOIA role · single-agency · internal/trusted
- **Statutory basis:** 5 USC 552(a)(4)(A) (fees), 5 USC 552(a)(6) (time limits)

## Summary
Front-line owner of a FOIA request. Triages incoming requests, sets the fee category, and runs
the statutory 20-working-day response clock. The default persona in the demo role-switcher.

## What they can do
- Triage FOIA requests at intake (`INTAKE_TRIAGE` status); route into the pipeline.
- Set the **fee category** per requester type (commercial / news-media-educational-scientific / other).
- Start and manage the **20-working-day** statutory response clock.
- Create, update, and delete FOIA requests; view pipeline KPIs and escalated requests.

## Constraints / authority limits
- Scoped to a **single agency** (`agencyId` is set, not null).
- Owns intake/triage, **not** the final release decision — that belongs to General Counsel.
- Does not produce records (Records Custodian) nor sign exemption determinations.

## Impact on the system
High. Controls request intake, triage routing, and the statutory clock — i.e. whether a request
enters the pipeline correctly and on time. Mis-triage or a missed clock is a compliance failure.

## Evidence (file:line)
- `frontend/src/app/models/roles.ts:19,47-51` — role + authority note
- `frontend/src/app/components/officer-dashboard/officer-dashboard.component.ts:23-100` — dashboard
- `services/foia-request-service/.../service/FoiaRequestService.java:77,116,142` — CREATE/UPDATE/DELETE

## Reviewer lens
> You are a FOIA Officer. Verify the migrated UI preserves correct intake triage, fee-category
> selection, and a visible, accurate 20-working-day clock. Flag anything that hides the clock,
> mis-routes triage, or lets a request skip intake.
