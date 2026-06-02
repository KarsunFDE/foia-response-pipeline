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
2. Requests are sorted based on priority, with HITL review available if prioritization is uncertain or disputed
3a. Retrieve relevant federal FOIA authority, likely exemption categories, and supporting source material
3b. Analyze the request against the retrieved authority and source material
4. (HITL Gate) Review proposed exemptions only after retrieval is complete, with cited authority, source snippets, and confidence visible
5. Retrieve and review relevant prior FOIA decisions or precedent tied to the scoped request
6. (HITL Gate) Review the prior decisions or precedent, and if scope is corrected or rejected, loop back through retrieval and analysis using the approved snapshot and prompt version
7. Based on the approved retrieved material, precedent, and gate outputs, the AI generates a recommendation for disposition, supporting rationale, citations, and confidence for HITL review
8. (HITL) Review the recommendation and decide the final disposition; if retrieval is missing, below threshold, or insufficiently grounded, escalate rather than silently continue

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
