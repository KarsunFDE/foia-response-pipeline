# Persona: System Administrator

- **Role id:** `sys_admin`
- **Class:** Cross-cutting / platform · **cross-tenant (root)** · no agency affiliation (`agencyId: null`)
- **Basis:** FedRAMP AC-2 (account management), AC-6 (least privilege)

## Summary
The platform root. Provisions users across all tenants, assigns/updates roles, resets MFA, and
rotates keys. The most powerful role in the system and the highest-value target.

## What they can do
- **Provision users** across tenants (`USER_PROVISION`).
- **Assign / update roles** (`USER_ROLE_UPDATE`).
- **Reset MFA** enrollment / recovery (`USER_MFA_RESET`).
- Rotate keys (referenced in authority note).

## Constraints / authority limits
- **Cross-tenant** (`agencyId: null`) — no agency scoping.
- Root-level trust: any over-grant here is total. Must itself be protected with MFA + strong,
  tamper-evident audit logging.
- Should not also hold operational decision roles (CO/SSA/GC) — separation of duties.

## Impact on the system
Critical. Can mint any role for any tenant and reset authentication — i.e. can manufacture the
authority of every other persona. The blast radius is the whole platform; sys_admin actions must
be the most heavily audited events in the system.

## Evidence (file:line)
- `frontend/src/app/models/roles.ts:32,121-125` — role + authority note
- `services/foia-request-service/.../controller/AdminUserController.java:12-59` — `/admin/users`
- `services/foia-request-service/.../service/UserService.java:34,44,55` — PROVISION / ROLE_UPDATE / MFA_RESET

## Reviewer lens
> You are a security reviewer modeling sys_admin abuse. Verify every admin action stays audited
> with actor identity, that role assignment cannot be self-escalated silently, and that the
> migration does not expose `/admin/*` to weaker auth. Flag any unaudited or default-allow admin path.
