# HITL Plan
The sponsor mandate, as received:

> *"Our FOIA officers are buried — every request has to be routed, screened for
> likely exemptions, and checked against past decisions, and the 20-working-day
> clock never stops. We want to pilot AI to triage incoming requests, surface the
> likely-exempt categories, and pull precedent from prior decisions — without ever
> releasing something that should have been withheld, and without an OIP or OIG
> reviewer being able to say the system made a release decision a human was
> supposed to make, or cited an exemption that doesn't exist."*

Some background on FOIA and what the role of a FOIA officer entails:

FOIA officers review incoming requests, identify responsive records, coordinate searches, assess applicable federal FOIA exemptions, and support legally compliant responses within statutory timelines.


## Rough Outline
1. AI intakes and analyzes requests 
2. Requests are sorted based on their priority (HITL may be needed to review whether or not the priorty sorting is correct?)
3. Based on the analysis of a given request, search and cite the likely-exempt categories
4. (HITL) Review the determined exemptions
5. Based on the analysis of a given request, look at the relevant prior FOIA decisions or precedent
6. (HITL) Review the prior decisions
7. Based on all of the analyzed information, the AI generates a recommendation for disposition, supporting rationale, and citations for HITL review
8. (HITL) Review the suggestion and decide on the final decision

## Decision Controls

- The system must not auto-release or auto-withhold any request.
- All final dispositions require human review and approval before any requester-facing action is taken.
- The system may generate recommendations, citations, and draft rationale, but it may not execute a final release decision.

## Recommendation Outcomes

- Full release
- Partial release with redactions
- Full withholding
- No responsive records
- Glomar response when legally applicable
- Referral or consultation with another agency or component
- Request for clarification or narrowing
- Administrative closure when procedurally required

- Any recommendation involving withholding or redaction must include:
  - cited exemption basis
  - foreseeable harm rationale when applicable
  - segregability analysis
  - supporting precedent or source authority

## Audit Logging

- Record an append-only audit trail for each request.
- Log prompt version, retrieved sources, recommendation output, reviewer actions, final disposition, and timestamps.
- Preserve sufficient detail to support reconstruction for oversight, including OIP or OIG review.

## Parallel Developer Workflows
- One workflow can focus on intake, routing, and priority handling.
- One workflow can focus on retrieval of FOIA law, precedent, and exemption grounding.
- One workflow can focus on final recommendation generation, reviewer handoff, and audit visibility.

## Example System Prompts by Phase

### 1. Intake / Triage
You are assisting with FOIA intake triage. Summarize the request, identify likely request type, flag urgency or ambiguity, and recommend routing and priority. Do not make a final release decision.

### 2. Exemption Analysis
You are assisting with FOIA exemption analysis. Review the request and retrieved legal or precedent material. Suggest likely applicable exemptions only when supported by cited authority. If support is weak or unclear, say so explicitly.

### 3. Recommendation Drafting
You are assisting a FOIA officer. Draft a recommendation for release or withholding based only on the analyzed request, cited exemptions, and retrieved precedent. Provide a concise justification. Do not present the result as final. A human reviewer must make the final decision.

### 4. Human Review Handoff
Prepare a concise review summary for a FOIA officer. Include the request summary, likely exemptions, supporting citations, confidence concerns, and the specific decision that requires human approval.
