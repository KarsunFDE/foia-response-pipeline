# foia-response-pipeline — Phase 1 PRD: AI Adoption

| | |
|---|---|
| **Product** | `foia-response-pipeline` — FOIA request processing platform |
| **Aspect** | `foia-processing` (anchor: FOIA.gov) |
| **Phase** | Phase 1 — AI Adoption |
| **Status** | Living draft — refined in planning sessions |
| **Owner** | Pair 3 |
| **Last updated** | 2026-05-28 |

> **This is a PRD, not a plan.** It states the problem, goals, boundaries, and
> what "done" looks like — the *what* and *why*. The *how* (endpoints, schemas,
> retrieval approach, gate primitives, thresholds) is left to the planning
> sessions and captured as ADRs. Requirements will change as we learn; material
> changes land in the [Change log](#13-change-log), and the
> [Open questions](#11-open-questions--to-plan) are the standing handoff to planning.

**Source of truth:** aspect commitment → [`../adrs/0001-foia-processing-commitment.md`](../adrs/0001-foia-processing-commitment.md) ·
rename trail + entities → [`../../domain-mapping.md`](../../domain-mapping.md) ·
inherited debt → [`../brownfield-debt.md`](../brownfield-debt.md) +
[`../pair-unique-debt.md`](../pair-unique-debt.md) · corpus → 5 USC 552 (FOIA) +
28 CFR 16 (DOJ FOIA regs) · scope caps →
`training-resources/instructor-handbook/per-pair-scope-boundaries.md`.

---

## 1. Background / sponsor objective

The sponsor mandate, as received:

> *"Our FOIA officers are buried — every request has to be routed, screened for
> likely exemptions, and checked against past decisions, and the 20-working-day
> clock never stops. We want to pilot AI to triage incoming requests, surface the
> likely-exempt categories, and pull precedent from prior decisions — without ever
> releasing something that should have been withheld, and without an OIP or OIG
> reviewer being able to say the system made a release decision a human was
> supposed to make, or cited an exemption that doesn't exist."*

That is the whole brief. It doesn't say which endpoints, which models, what
"triage" means, or where a human must stay in the loop — that's ours to plan.
Phase 1 disseminates it to a single intent: **introduce AI into the intake-triage
→ exemption-analysis stage, with every record-release (irreversible) decision
routed through a human, and every AI output traceable to a real FOIA exemption /
precedent and an accountable actor.**

Phase 1 is **adoption**, not modernization. We add AI on top of the platform as
it stands; fixing the legacy stack is Phase 2 (§12).

## 2. Current state

`foia-response-pipeline` was generated from the `acquire-gov` template and carries
the same four-service shape, renamed to the FOIA domain:

| Service | Stack | Port |
|---------|-------|------|
| `frontend/` | Angular 17 SPA — FOIA-officer UX | 4200 |
| `services/api-gateway/` | Spring Boot 2.7.18 + OAuth2 Resource Server (Java 11) | 8080 |
| `services/foia-request-service/` | Spring Boot 2.7.18 + Postgres + MongoDB (Java 11) | 8081 |
| `services/redaction-review-service/` | Spring Boot 2.7.18 (Java 11) | 8082 |
| `services/ai-orchestrator/` | Python 3.11 + FastAPI + LangChain v1.0 (Bedrock) | 8000 |

(`redaction-proposer-service` and `timeline-tracker-service` are anticipated but
not yet scaffolded — added in planning only if the capped redaction stretch needs
them.)

The platform runs, but the AI path today returns **raw, ungrounded model output
with no validation** — it will confidently cite a 5 USC 552 exemption that doesn't
apply or doesn't exist. In FOIA the cost is asymmetric: a wrong call can **leak a
record that should have been withheld** (irreversible) or trigger an appeal. That
is the defensibility problem the sponsor named, and it's the thread Phase 1 pulls.

The platform carries **12 inherited debt items** ([`brownfield-debt.md`](../brownfield-debt.md))
shared with all pairs, plus **5 pair-unique items** ([`pair-unique-debt.md`](../pair-unique-debt.md)).
Adoption work surfaces — and may incidentally close — a few; deliberate
modernization of the rest is Phase 2.

> **Domain note — inverted threat model.** Unlike the other aspects, the
> **requester may be adversarial** (journalists, watchdog orgs, opposition
> researchers). The core risk is **release reliability** — false negatives leak,
> false positives trigger appeals — and the **statutory 20-working-day clock**
> dominates NFRs. This shapes Phase 1's HITL gate (on release) above all else.

## 3. Goals

| # | Goal | Done = |
|---|------|--------|
| G1 | Speed up request triage | A FOIA officer gets an AI triage (routing + likely-exempt categories) on an incoming request, on demand. |
| G2 | Ground every AI judgment in real FOIA law | Exemption flags and answers cite the actual 5 USC 552 / 28 CFR 16 source or a prior decision; ungrounded ones are withheld, not shipped. |
| G3 | Make any release decision safe | Every record-release decision runs through a hard human gate — the system never releases on its own. |
| G4 | Be auditable by default | Every AI-assisted decision is reconstructable for OIP/OIG: who, what, when, under which authority. |
| G5 | Be measurably correct | AI quality is gated by automated evaluation, and regressions are caught before they ship. |

## 4. Non-goals (Phase 1)

Boundaries are deliberate and **especially sharp here — FOIA naturally explodes.**
**Phase 1 is hard-capped to two subsystems: (1) intake + triage, (2) precedent
search.** Out of scope:

- ❌ **Full redaction proposer/reviewer pipeline** — the multi-agent shape may be *attempted* in W3 only if budget allows; otherwise a single-agent flag-suggester. Not a Phase 1 commitment.
- ❌ **Appeals workflow** — entirely out.
- ❌ **Records-retention** deep-dive — entirely out.
- ❌ **Statutory-deadline calculation engine** — a simple SLA timer only; no calendar/business-day logic.
- ❌ Multi-agency cross-routing — single-agency simulator only.
- ❌ **Real PII redaction against real corpora** — synthetic only (real CUI/FedRAMP compliance is out).
- ❌ Production FOIA portal UX; DOJ OIP reporting integration; real agency document storage (synthetic S3 + mock docs).
- ❌ Framework/runtime modernization; AI-security hardening of inherited debt; AIOps. Angular major hop. Managed Bedrock products.

## 5. Users

| Persona | Role | What Phase 1 gives them |
|---------|------|--------------------------|
| **FOIA Officer** | Owns the request; routes + decides | AI triage + likely-exempt flags + precedent to review; the release-decision authority. |
| **General Counsel** | Adjudicates hard exemption calls | Precedent and grounded exemption reasoning to support a call. |
| **Requester** *(potentially adversarial)* | Submits the request | A faster, defensible response (via the officer) — never an accidental over-release. |
| **OIP (DOJ oversight) / OIG** | After-the-fact accountability | A replayable trail: who decided to release/withhold what, when, under which exemption. |

## 6. Capability requirements

Three capabilities; the first two are the Phase 1 centerpiece, the third is gated
by budget. Stated as outcomes — **the planning sessions decide how.** (Aspect
agent shape is **multi-agent**, but see the cap in REQ-AGT-1.)

### M1 — LLM-assisted intake triage
- **REQ-AID-1** The platform triages an incoming FOIA request — routes it to the right office and surfaces likely-exempt categories. *Done:* an officer gets a reviewable triage result on demand.
- **REQ-AID-2** AI output is safe to consume — no malformed or ungrounded content silently passes downstream. *Done:* bad model output is caught before it reaches another service or the officer.
- **REQ-AID-3** AI usage is cost-controlled and observable (especially under large responsive-document uploads). *Done:* cost is attributable per tenant/feature and runaway spend is bounded.
- **REQ-AID-4** No triage outcome that affects a release is finalized without officer approval *(HITL)*. *Done:* finalization is impossible without a recorded human decision.

### M2 — Grounded retrieval (precedent search)
- **REQ-RAG-1** Exemption judgments come from the actual 5 USC 552 / 28 CFR 16 corpus and prior FOIA decisions, with citations. *Done:* every authoritative flag/answer traces to a source exemption or prior decision.
- **REQ-RAG-2** Low-confidence or ungrounded answers are withheld and escalated to a human, never shipped *(HITL)*. *Done:* below-bar answers route to review instead of returning. *(In FOIA, "withhold by default" is the safe failure.)*
- **REQ-RAG-3** One agency can never retrieve another agency's requests or decisions. *Done:* cross-tenant retrieval is impossible and proven by test.
- **REQ-RAG-4** Retrieval quality is measured and protected from regression. *Done:* an evaluation gate blocks changes that degrade grounding.

### M3 — Release-decision gate (redaction assist is budget-capped)
- **REQ-AGT-1** An assisted exemption/redaction flow runs on synthetic requests. **Baseline = a single-agent flag-suggester; the multi-agent proposer + reviewer is a W3 stretch, only if budget allows.** *Done:* the flow produces exemption/redaction suggestions feeding a gated release step.
- **REQ-AGT-2** Every **record-release** decision (irreversible — a released record cannot be un-released) stops for the officer; the agent cannot release on its own *(HITL)*. *Done:* no code path auto-releases a record or auto-overrides a withhold.
- **REQ-AGT-3** A paused decision survives a real-world human delay (within the 20-day clock) and resumes without loss or regeneration. *Done:* a run pauses for the officer and resumes intact after a restart.
- **REQ-AGT-4** Every gated decision is auditable for OIP/OIG — who decided to release/withhold, what they saw, under which exemption. *Done:* a reviewer can reconstruct each release decision from the trail alone.
- **REQ-AGT-5** The data answers the relational questions an officer asks (e.g. "prior decisions on similar requests / by this requester"). *Done:* the key cross-record question is answerable at interactive speed. *(Lightest of the five — keep it simple given the cap.)*

## 7. Principles (cross-cutting)

Non-negotiable; *how* they're implemented is planned.

- **Authority over accuracy.** Gates exist for accountability, not model quality. The record-release decision is a **hard** gate; confidence never downgrades it.
- **Withhold by default.** When grounding or exemption analysis is uncertain, the safe failure is to withhold and escalate — never release on a guess.
- **Right-sized HITL.** Classify by reversibility × blast-radius. Gate every release; don't gate trivial routing.
- **Grounded or withheld.** No authoritative exemption flag/answer ships without a real citation or precedent.
- **Auditable by default.** Sensitive/AI-assisted decisions write an append-only, OIP/OIG-replayable record.
- **Synthetic + FedRAMP-safe.** Synthetic data only (no real PII/CUI); Bedrock is the sole LLM path (ADR `0002`); no direct third-party model API.
- **Eval as the gate.** Quality is proven by automated evaluation in CI, not manual inspection.

## 8. Domain model

Core entities (full inventory in [`domain-mapping.md`](../../domain-mapping.md)):
`FoiaRequest` (primary) and `RedactionReview` (review), across the **in-scope**
stages **intake-triage → exemption-analysis**. (Later stages — redaction-proposal,
hitl-review, response, appeal — exist in the model but are out of Phase 1 scope per
§4.) Officer work is relational ("prior decisions on similar requests"), so the
model must support the key cross-record question at interactive speed (REQ-AGT-5).
The repo inherits ~15 acquire-gov entities as raw material to repurpose (e.g.
`ClauseLibraryEntry` → exemption library b(1)–b(9)) or delete in Phase 2 — not
Phase 1 scope.

## 9. Success metrics & Phase 1 exit

Done when M1 + M2 work end to end (M3 to the gated-release boundary) and the
following hold (these are also the gate dimensions):

| Dimension | Exit outcome |
|-----------|--------------|
| Agent-flow architecture | The triage → exemption → gated-release flow runs end to end on synthetic data and survives a human-delay pause/resume. |
| Federal-authority semantics | Every hard gate names its governing authority (5 USC 552 exemptions); no record can be auto-released. |
| HITL appropriateness | Gates are right-sized by reversibility × blast-radius — every release is gated, routing isn't over-gated. |
| Relational integration | The officer's prior-decision question is answerable within an interactive budget. |
| Debt acknowledgement | The team can name which inherited/unique debt their AI work touched, surfaced, or closed — and which is deferred to Phase 2. |

Product signals: triage turnaround → minutes (G1); zero ungrounded authoritative
exemption flags in evaluation (G2); **zero auto-releases**, 100% of release
decisions produce an audit record (G3/G4).

## 10. Constraints & scope caps

- **Two subsystems only.** Intake+triage (centerpiece) and precedent search. Nothing else.
- **One core entity, one workflow-stage MVP.** `FoiaRequest` + intake triage.
- **Redaction multi-agent is a stretch, not a commitment.** Single-agent flag-suggester is the baseline; full proposer/reviewer only if W3 budget allows.
- **Synthetic PII only.** No real PII/CUI; precedent search over a synthetic decision set only.
- **Single agency.** No multi-agency cross-routing.
- **SLA timer only.** No statutory-deadline calculation engine.
- **Adopt, don't modernize.** Don't pre-fix inherited debt that Phase 2 owns; surface it, note the blast radius, defer it.

## 11. Open questions / to-plan

The deliberate handoff to planning — decided there and captured as ADRs.

- Triage output schema + the routing / likely-exempt-category fields an officer needs.
- Retrieval approach (chunking, embedding, dense/sparse/hybrid, reranking) over 5 USC 552 + 28 CFR 16 + a synthetic prior-decision set.
- Exemption-category model: rules-based vs. model-assisted, and how (b)(1)–(b)(9) are represented.
- The "withhold / escalate" confidence bar and how it's measured (FOIA-conservative).
- Whether the multi-agent redaction stretch is attempted in W3 (budget call) — and if so, the proposer/reviewer topology. **Sequencing:** like all agentic work it depends on the W2 LangChain v1.0 migration (Item 5) + adding `langgraph`; not built ahead of W2.
- Release-gate primitives + how a paused release is persisted within the 20-day clock.
- How far correlation/tracing is threaded in Phase 1 vs. deferred to Phase 2.
- Which inherited/unique debt items are in-bounds to close incidentally vs. strictly deferred.

## 12. Phase 2 outline (refined at Phase 1 close-out)

Sketch only. Phase 2 = **modernization + operationalization**: framework/runtime
modernization; Presidio + custom PII detector pipeline for CUI categories
(**synthetic corpora only**); HITL audit trail for every redaction OK/override
(feeds the eval report); AIOps on response-timeline drift (which requests are at
statutory-miss risk against the 20-working-day clock); AI-security hardening of
inherited + unique debt; client deliverability. A dedicated Phase 2 PRD supersedes
this section.

## 13. Change log

| Date | Change | Driver |
|------|--------|--------|
| 2026-05-28 | Initial Phase 1 PRD disseminated from sponsor objective (brief altitude). | Phase 1 kickoff |
