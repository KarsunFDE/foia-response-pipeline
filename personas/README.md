# Personas

Stakeholder/role definitions for the FOIA-response-pipeline project. Each file describes a
**role** — its authority, what it can do, its constraints, and its impact on the system — so
Claude can load any one as a review lens or context "persona" later.

These are **roles, not people**. No specific named accounts are recorded; the demo fixtures in
`frontend/src/app/models/roles.ts` attach example display names (e.g. "Dana Reeves") for the
instructor role-switcher — those are intentionally omitted here.

> **Authoritative source:** `frontend/src/app/models/roles.ts` (the `Role` union + `ROLE_PROFILES`).
> Capabilities/constraints are corroborated against the Java services and the AI orchestrator
> workflow. Every persona file cites `file:line` evidence.

---

## How the roles split

The system is mid-migration from an inherited **acquisition** platform to a **FOIA-response**
platform (see `roles.ts:13-15`). That history shapes the role set:

### Active FOIA roles (5 USC 552, 28 CFR 16)
| Persona | Role id | Scope | One-line authority |
|---|---|---|---|
| [FOIA Officer](./foia-officer.md) | `foia_officer` | single agency | Triage, fee category, run the 20-working-day clock |
| [General Counsel](./general-counsel.md) | `general_counsel` | single agency | Approve/withhold release; sign exemptions (b) |
| [Records Custodian](./records-custodian.md) | `records_custodian` | single agency | Locate/produce records; assert (b)(1)/(b)(7) |
| [Requester](./requester.md) | `requester` | external / untrusted | Submit requests, track, appeal (inverted threat model) |
| [OIP Oversight](./oip-oversight.md) | `oip_oversight` | cross-tenant, read-only | FOIA-Improvement-Act compliance reporting |

### Legacy acquisition roles (FAR — inherited, repurposed/removed W4–W5)
| Persona | Role id | Scope | One-line authority |
|---|---|---|---|
| [Contracting Officer (CO)](./contracting-officer.md) | `contracting_officer` | single agency | Sign award, amend, terminate, unseal proposals |
| [Contract Specialist (CS)](./contract-specialist.md) | `contract_specialist` | single agency | Draft solicitations/amendments; cannot sign award |
| [Program Manager (PM)](./program-manager.md) | `program_manager` | single agency | Requirements + CPAR draft |
| [Source Selection Authority (SSA)](./source-selection-authority.md) | `ssa` | single agency | Final award decision (SSDD) |
| [Evaluator (TEP)](./evaluator.md) | `evaluator` | single agency | Score proposals against Section M |
| [Vendor / Contractor](./vendor.md) | `vendor` | external, multi-agency | Submit proposals; CPAR rebuttal; debrief |
| [OIG Reviewer](./oig-reviewer.md) | `oig_reviewer` | cross-tenant, read-only | Open findings; remediation tracking |

### Cross-cutting / system actors
| Persona | Role id | Scope | One-line authority |
|---|---|---|---|
| [System Administrator](./sys-admin.md) | `sys_admin` | cross-tenant (root) | Provisioning, role assignment, MFA reset, key rotation |
| [Public / Unauthenticated](./public.md) | `public` | unauthenticated | Read-only on `/api/public/*` |
| [AI Orchestrator](./ai-orchestrator.md) | _(non-human)_ | service actor | Triage/redaction/SSDD drafts — non-authoritative, HITL-gated |

---

## Notes on authority & threat model
- **Separation of duties (FedRAMP AC-5):** drafting authority and signing authority are split
  (CS drafts / CO+SSA sign; PM drafts CPAR; Evaluator scores / SSA decides).
- **Inverted threat model:** `requester`, `vendor`, and `public` are external/untrusted —
  read-only or narrowly scoped (`roles.ts:5-7`, `:38`).
- **AI is never the decider:** the orchestrator's outputs are always gated behind a human
  approve step (HITL); see [ai-orchestrator.md](./ai-orchestrator.md).
