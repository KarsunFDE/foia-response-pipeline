# Persona: Public / Unauthenticated Visitor

- **Role id:** `public`
- **Class:** Cross-cutting · **unauthenticated** · no agency affiliation (`agencyId: null`)

## Summary
Anyone hitting the system without credentials. Read-only on the public surface
(`/api/public/*`) — published FOIA requests and public opportunities.

## What they can do
- **Read-only** access on `/api/public/*`.
- View published FOIA requests and public opportunities.

## Constraints / authority limits
- **No authentication** (`agencyId: null`); read-only.
- Must never reach authenticated/internal data.

## Impact on the system
Low in capability, **high in risk**. The `/api/public/*` surface is the documented vulnerable
surface (Debt Item 1 — JWT signature-skip on `/api/public/*`). It is the first thing an attacker
touches, so any migration must not widen what unauthenticated callers can read or do.

## Evidence (file:line)
- `frontend/src/app/models/roles.ts:11,33,127-131` — role + Item-1 surface note
- `services/foia-request-service/.../controller/PublicOpportunitiesController.java` — `/api/public/*`

## Reviewer lens
> You are a security reviewer probing the unauthenticated surface. Verify the migration keeps
> `/api/public/*` strictly read-only and does not extend it with internal data or write routes —
> and treat the Item-1 JWT signature-skip as a live risk. Flag any new public-reachable mutation.
