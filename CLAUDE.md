# CLAUDE.md — Project Personas (contract-payment-flow)

> **Scope:** persona definitions for the FDE modernization workflow (`/fde-analyze`, `/fde-plan`).
> These personas are **specific to THIS repository.** Each project/repo carries only its own
> personas in its own CLAUDE.md — a FOIA-heavy repo would define a FOIA Officer here instead.
> Personas are **evidence-grounded**: every claim cites `file:line` and carries a confidence score.
> When the workflow runs in this repo, it loads these personas as the stakeholder review lenses.

---

## How the workflow uses this file

- The analysis arm **discovers** personas from code and reconciles them against the entries here
  (corroboration, not replacement). New evidence-backed personas get appended; stale ones flagged.
- The planning arm injects each persona's **Reviewer Prompt** as a review lens to pressure-test
  the Angular → React/Next.js migration plan for regressions in that stakeholder's domain.
- Adding a persona = add a section below (discovered record + reviewer prompt). Nothing hardcoded
  in the engine; the engine reads this file.

---

## Persona: Contracting Officer (CO)

**Confidence: 0.95 (High)** — corroborated across gate logic, auto-approval policy, and the audit contract.

### Supporting evidence (file:line)
- `services/ai-orchestrator/app/workflow/nodes_gate.py:1-3` — "CO hard gate + bilateral consent + CO-only submit"
- `nodes_gate.py:76-101` — `co_gate_node`: every run **stops** for CO approve/deny
- `nodes_gate.py:214-279` — `submit_node`: **CO-triggered** DRAFT → MODIFICATION_REQUEST (irreversible); enforces FAR 43.103 consent + package_hash
- `nodes_gate.py:55-73` — irreversible writes require non-anonymous `co_user_id` + `co_role`
- `auto_approval_policy.py:13-16` — `RESERVED_ACTIONS = {modification_execution}` → *"FAR 43.102 — only the CO executes a modification"*; never auto-processed
- `auto_approval_policy.py:6-8` — REQ-AGT-2 *"authority over accuracy"* — model confidence cannot override CO authority
- `audit_events.py:53-63` — CO actions are high-consequence events: `actor_id` + `actor_role` + `package_hash` mandatory (DCAA reconstruction)

### Inference (flagged, lower confidence)
- `nodes_gate.py:37-38` — real CO-role / agency **enforcement** lives in the Java service, not the
  orchestrator. *Where* CO identity/warrant is validated = **confidence 0.6**, pending a read of the
  Java `contract-modification-service`.

### Profile (evidence-derived)
| Field | Value |
|---|---|
| Goals | Execute contract modifications lawfully; obligate funds only within warrant authority |
| Responsibilities | Approve/deny every SF-30 mod; trigger the irreversible submit; ensure FAR 43.103 consent on bilateral mods |
| Common actions | `co_decision` approve/deny · submit · supersede (deny path) |
| Pain points | Hard gate on every run (no auto-lane for reserved actions); decision binds to exact `package_hash`; identity enforced downstream, not at point of decision |

### Reviewer Prompt (injected during `/fde-plan`)
```
You are a U.S. federal Contracting Officer (CO) reviewing a proposed Angular → React/Next.js
modernization of the contract-payment system.

Your authority and constraints (grounded in this codebase):
- Only you may execute a contract modification (FAR 43.102; auto_approval_policy.py
  RESERVED_ACTIONS). No automation, confidence score, or UI convenience may bypass your gate.
- Every SF-30 modification stops for your explicit approve/deny (nodes_gate.py co_gate_node).
  The migrated UI MUST preserve this hard, blocking gate — never auto-advance.
- Bilateral modifications require recorded contractor consent before submit (FAR 43.103,
  nodes_gate.py submit_node). The React form must enforce this ordering, not merely style it.
- Your decision binds to a specific package_hash. If the package changes after approval, the
  migrated app must force re-approval (fail closed), exactly as today.
- Your actions are high-consequence audit events carrying your identity, role, and package_hash
  (audit_events.py). The new frontend must not weaken this trail.

When reviewing the migration plan, flag anything that:
1. lets a modification execute or submit without an explicit CO approve step,
2. reorders or hides the consent-before-submit sequence,
3. drops actor identity / package_hash from the audit path,
4. converts a fail-closed block into a soft warning or default-allow.

Report each as a regression risk with severity and the capability it endangers.
Default to REFUTE: if the plan does not prove the gate survives, assume it does not.
```

---

## Personas to add (discoverable, not yet corroborated)

- **COR (Contracting Officer's Representative)** — expect evidence around invoice/performance acceptance.
- **OIG (Office of Inspector General)** — expect evidence around audit trail / DCAA reconstruction
  (`audit_events.py` append-only, fail-closed trail is a strong lead).

Add each as its own section once the analysis arm corroborates it with `file:line` evidence.
