# ADR 0005 — Agentic FOIA triage workflow: stage boundaries, tool-vs-AI split, and HITL gates

Status: Accepted
Date: 2026-06-09
Decision-makers: Pair 3 cohort

## Context

The sponsor mandate (`docs/hitl-plan.md`) asks for an AI pilot that triages
incoming FOIA requests, surfaces likely-exempt categories, and pulls precedent
from prior decisions — **without** ever auto-releasing a record that should have
been withheld, and without an OIP/OIG reviewer being able to say the system made
a release decision a human was supposed to make or cited an exemption that does
not exist.

`docs/hitl-plan.md` already fixes the policy controls (no auto-release /
auto-withhold, mandatory human approval, append-only audit, recommendation
outcomes, per-phase system prompts). What it does not yet pin down — and what
this ADR records — is the **engineering shape** of the workflow:

- which steps are deterministic tool calls vs. AI (LLM) calls,
- where the human-in-the-loop (HITL) gates sit relative to those steps,
- the typed payload (Pydantic models) passed between stages,
- which Claude model each agent uses and why,
- what context is held at which scope (conversation / workflow / system).

This is a design decision because the tool-vs-AI split and the gate placement
are the load-bearing controls that keep the system FOIA-conservative. Getting
them wrong (e.g. letting an LLM call do score filtering, or placing a gate after
disposition instead of before) reintroduces exactly the failure modes the
sponsor named.

## Decision

### 1. Stage pipeline

The workflow runs as the staged pipeline in `docs/hitl-plan.md` §Rough Outline,
made explicit here as alternating tool/AI steps with three HITL gates:

```
[user input] FOIA request + requester identity/contact
   │
   ├─ AI    Intake: validate required fields, flag missing/ambiguous
   ├─ AI    Classify: request type, likely-exempt categories
   ├─ AI    Route: target agency/component + priority
   │
   ├─ TOOL  Retrieve federal authority + exemption grounding (Atlas, ADR 0003/0004)
   ├─ TOOL  Score filtering / top-k cut
   ├─ AI    Analyze request against retrieved authority
   │
   ├─ GATE 1  Review proposed exemptions (cited authority + snippets + confidence visible)
   │
   ├─ TOOL  Retrieve prior decisions / precedent (prior examples)
   │
   ├─ GATE 2  Review prior decisions; if scope corrected/rejected → loop back
   │          through retrieval + analysis on the approved snapshot + prompt version
   │
   ├─ AI    Generate disposition recommendation + rationale + citations + confidence
   │
   └─ GATE 3 (RISKY)  Review recommendation, decide FINAL disposition;
              escalate if retrieval missing / below threshold / under-grounded
```

### 2. Tool calls vs. AI calls

Deterministic, auditable, or policy-bearing work is a **tool call**, not an LLM
call. The LLM never does retrieval, ranking, or thresholding itself.

| Tool calls (deterministic / retrieval / code) | AI calls (LLM reasoning) |
|---|---|
| Pull prior examples / precedent | Validate required fields present |
| Retrieval from MongoDB Atlas (ADR 0003/0004) | Classify likely-exempt categories |
| Score filtering / top-k cut | Routing (agency/component + priority) |

Rationale: score filtering and retrieval are reproducible and must appear
verbatim in the audit trail. An LLM "deciding" what cleared a threshold is
neither reproducible nor defensible to OIP/OIG. Field validation, exemption
classification, and routing are judgment tasks where the LLM **assists** — it
proposes, a human disposes.

### 3. HITL gates — risk-ranked

Three gates, placed so a human sees grounded material *before* anything
consequential:

- **Gate 1 — Review proposed exemptions** (lower risk). Fires only after
  retrieval is complete, with cited authority, source snippets, and confidence
  visible. Prevents a fabricated/unsupported exemption from propagating.
- **Gate 2 — Review prior decisions / precedent** (lower risk). Reviewer can
  correct or reject scope; rejection loops back through retrieval + analysis on
  the **approved snapshot and prompt version** (no silent drift).
- **Gate 3 — Final disposition** (**RISKY** — the irreversible, requester-facing
  decision). Human reviews the AI recommendation and decides the final
  disposition. The system never executes a release/withhold itself. If retrieval
  is missing, below threshold, or insufficiently grounded → **escalate, do not
  silently continue.**

This satisfies `hitl-plan.md` §Decision Controls: no auto-release/withhold; all
final dispositions require human approval before any requester-facing action.

### 4. Inter-stage payload (Pydantic models)

State passed between stages is typed (Pydantic v2, consistent with
`ai-orchestrator`). Fields, drawn from the agreed list:

```python
class FoiaTriageState(BaseModel):
    request_id: str                    # FOIA request id (carries on `proposal_id`; see domain-mapping.md)
    foia_request: str                  # raw request text
    requester_info: RequesterInfo      # identity + contact
    target_agency: str | None          # component/agency to route to
    date_range: DateRange | None       # scoped record date range
    attachments: list[Attachment]      # supporting files
    content_info: dict                 # extracted/structured content descriptors
    keywords: list[str]                # search/scoping terms
    citations: list[Citation]          # cited federal authority (5 USC 552 / 28 CFR 16 / OIP)
    missing_fields: list[str]          # required-field gaps
    clarification_status: ClarificationStatus  # needs-clarification | clear
```

Citations and content carry the FOIA-domain meaning even where legacy keys
(`far_part`, `proposal_id`, `clause_id`) are preserved per
`domain-mapping.md` — do not rename them.

### 5. Model selection

**Claude Sonnet** (default `anthropic.claude-3-7-sonnet-…`, per `.env.example`
and ADR 0002) for the intake, classification, exemption-analysis, and routing
agents. Strong enough reasoning for federal-accuracy classification, exemption
analysis, and routing **without Opus cost**. Right-sized for the accuracy bar.
Revisit per-agent (e.g. Opus for recommendation drafting) only if eval shows
Sonnet under-grounding on disposition rationale — record as a follow-up ADR, not
a mid-flight switch.

### 6. Prompt shape (every agent)

Each agent system prompt must:
1. State the specific assisting role ("You are assisting with FOIA intake
   triage.").
2. Enumerate the tasks for that role.
3. State explicitly that the AI does **not** make the final decision.
4. Surface what it is assisting with, what the prior decisions were, and that a
   human reviewer decides.

Canonical per-phase prompts live in `docs/hitl-plan.md` §Example System Prompts.

### 7. Context scope

| Scope | Held | Examples |
|---|---|---|
| **Conversation** (single request thread) | recommendation output, review status, confidence scores | the in-flight recommendation a reviewer is looking at |
| **Workflow** (a request's full lifecycle) | request, citations, previous decisions, final disposition | carried across stages / gate loop-backs |
| **System** (across multiple conversations) | categories, request-type labels | reusable taxonomies / label sets |

Recommendation output is **conversation-only** — it is never promoted to system
scope, so a draft recommendation cannot leak into another request's context.

## Consequences

- Retrieval and score filtering stay out of the LLM, so the audit trail
  (`hitl-plan.md` §Audit Logging) records reproducible tool I/O, not LLM prose.
- Three gates add reviewer load by design; that is the point — nothing
  uncalibrated reaches a requester-facing action without a human.
- Gate 2 loop-back must re-run on the approved snapshot + pinned prompt version,
  so retrieval/prompt drift between attempts is impossible.
- Typed inter-stage state makes the workflow testable stage-by-stage and gives
  the audit log a stable schema to serialize.

## Alternatives considered

1. **Let the LLM do retrieval + scoring (single mega-agent).** Rejected — not
   reproducible, not auditable, and an LLM "passing a threshold" is
   indefensible to OIP/OIG.
2. **Single final gate only (gate at disposition).** Rejected — an unsupported
   exemption or bad scope would propagate all the way to the final reviewer with
   no earlier checkpoint; gates 1/2 catch grounding failures early and cheap.
3. **Opus for all agents.** Rejected on cost — Sonnet meets the federal-accuracy
   bar for classification/analysis/routing; reserve any Opus use for a later,
   eval-justified per-agent decision.
4. **Untyped dict state between stages.** Rejected — loses validation, makes the
   audit schema unstable, and invites silent field drift across the gate
   loop-back.

## Follow-up work

- Define the concrete Pydantic models in `ai-orchestrator/app/` and wire the
  `/agent/intake-triage` endpoint to emit `FoiaTriageState`.
- Pin prompt versions per agent so Gate 2 loop-back can reference an exact
  version.
- Eval-gate Sonnet on disposition-rationale grounding; open a follow-up ADR if
  an Opus per-agent override is warranted.
