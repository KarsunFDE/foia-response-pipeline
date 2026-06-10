# Agentic FOIA Triage Workflow — Diagram

Visualizes the workflow specified in [ADR 0005](adrs/0005-agentic-foia-triage-workflow.md)
and [`hitl-plan.md`](hitl-plan.md). Node shape/color encodes the tool-vs-AI-vs-gate
split that ADR 0005 §2–3 makes load-bearing.

**Legend** — 🟦 User input · 🟩 AI (LLM) call · 🟧 Tool call (deterministic /
retrieval) · 🟥 HITL gate (human approval).

```mermaid
flowchart TD
    %% ---- User input ----
    U([User: FOIA request + requester identity/contact]):::user

    %% ---- AI intake/classify/route ----
    A1[AI · Intake: validate required fields<br/>flag missing / ambiguous]:::ai
    A2[AI · Classify: request type<br/>+ likely-exempt categories]:::ai
    A3[AI · Route: target agency/component<br/>+ priority]:::ai

    %% ---- Retrieval + analysis ----
    T1[Tool · Retrieve federal authority<br/>+ exemption grounding · Atlas]:::tool
    T2[Tool · Score filter / top-k cut]:::tool
    A4[AI · Analyze request<br/>against retrieved authority]:::ai

    %% ---- Gate 1 ----
    G1{{HITL Gate 1 · Review proposed exemptions<br/>cited authority + snippets + confidence}}:::gate

    %% ---- Precedent retrieval ----
    T3[Tool · Retrieve prior decisions<br/>/ precedent · prior examples]:::tool

    %% ---- Gate 2 ----
    G2{{HITL Gate 2 · Review precedent<br/>correct / reject scope?}}:::gate

    %% ---- Recommendation ----
    A5[AI · Generate disposition recommendation<br/>+ rationale + citations + confidence]:::ai

    %% ---- Gate 3 ----
    G3{{HITL Gate 3 · RISKY · Review recommendation<br/>decide FINAL disposition}}:::gate

    ESC[/Escalate · retrieval missing<br/>below threshold / under-grounded/]:::esc
    FIN([Final disposition<br/>human-approved, requester-facing]):::user

    %% ---- Edges ----
    U --> A1 --> A2 --> A3 --> T1 --> T2 --> A4 --> G1
    G1 -->|approved| T3 --> G2
    G2 -->|scope ok| A5
    G2 -->|scope corrected / rejected| T1
    A5 --> G3
    G3 -->|grounded| FIN
    G3 -->|insufficient| ESC

    %% ---- Styles ----
    classDef user fill:#1f6feb,stroke:#0d326b,color:#fff;
    classDef ai   fill:#238636,stroke:#0f5323,color:#fff;
    classDef tool fill:#bf8700,stroke:#7a5600,color:#fff;
    classDef gate fill:#cf222e,stroke:#82071e,color:#fff;
    classDef esc  fill:#6e7681,stroke:#3d4148,color:#fff,stroke-dasharray:4 3;
```

## Notes

- **Gate 2 loop-back** re-enters at retrieval (`T1`) and re-runs analysis on the
  **approved snapshot + pinned prompt version** — no silent drift (ADR 0005 §3).
- **LLM never retrieves or thresholds.** `T1`/`T2`/`T3` are deterministic tool
  calls so the audit trail records reproducible I/O, not LLM prose.
- **All three gates are human approval points;** Gate 3 is the only
  irreversible, requester-facing decision — the system never auto-releases or
  auto-withholds.
- Every AI node runs **Claude Sonnet** with an assisting-role prompt that states
  the AI does not make the final decision (ADR 0005 §5–6).
