# Persona: AI Orchestrator (Non-Human Actor)

- **Actor id:** `ai-orchestrator` (audit actor string; not a `Role` in `roles.ts`)
- **Class:** System / service actor · **non-authoritative** · Human-In-The-Loop (HITL) gated

## Summary
The autonomous analysis engine. Triages requests, retrieves federal authority, proposes redactions
and SSDD drafts — but **never makes a final decision**. Every output is gated behind a human
approve step. Included as a persona because it acts in the workflow and appears in the audit trail.

## What it can do
- **Triage** FOIA requests (intake analysis).
- **Retrieve** federal authority (FAR, FOIA exemptions, precedent).
- **Propose** redaction factors; run a deterministic, auditable score filter.
- **Draft** SSDDs (Source Selection Decision Documents).

## Constraints / authority limits
- **No independent authority** — all outputs gated behind HITL human approval.
- Cannot publish exemption determinations without **General Counsel** sign-off.
- Cannot make award decisions without **SSA** approval.
- "Authority over accuracy": model confidence never overrides a human authority's decision.
- All actions audit-logged under the `ai-orchestrator` actor for traceability.

## Impact on the system
High assistive value, **zero decision authority by design**. It speeds high-consequence work but
is structurally prevented from being the decider — the gates that enforce this are the property
most worth protecting in any migration.

## Evidence (file:line)
- `services/ai-orchestrator/app/main.py` — analysis / redaction proposal entry
- `services/ai-orchestrator/app/triage_workflow.py:7-26` — HITL gates; AI does not make final decisions
- `services/redaction-review-service/.../service/RedactionReviewService.java:135` — SSDD_DRAFT → human approval
- Project `CLAUDE.md` — auto-approval policy / reserved actions / "authority over accuracy"

## Reviewer lens
> You are reviewing the AI orchestrator's role boundary. Verify every AI output (triage, redaction,
> SSDD) remains a proposal gated behind an explicit human approve step, that model confidence can
> never auto-advance a decision, and that AI actions stay in the audit trail. Flag any path where
> an AI output becomes effective without human sign-off.
