---
name: persona-synthesis
description: Turn discovered persona evidence into an evidence-grounded reviewer-lens system prompt. Use when the analysis has surfaced a stakeholder (e.g. Contracting Officer, FOIA Officer) from code/docs and you need a reusable persona definition + review prompt. Corroborates against the repo's CLAUDE.md personas.
---

# Persona Synthesis

Personas are **discovered from the repository, never hardcoded.** This skill converts raw discovery evidence into (a) a persona record and (b) a reviewer prompt the planning arm injects.

## Evidence sources (infer personas from)
Route names · API names · permissions · roles · DB entities/enums · UI labels · documentation/README · service names · audit records · domain regulation references (e.g. FAR clauses).

## Corroborate against CLAUDE.md
The repo's `CLAUDE.md` holds this project's curated personas. For each discovered persona:
- **Code + CLAUDE.md agree** → confirmed, raise confidence.
- **CLAUDE.md only / README only** → flag as ghost (documented, no code evidence).
- **Code only, not in CLAUDE.md** → new persona; propose appending it (with file:line evidence).

## Persona record (output)
```
Persona: <name>
Confidence: <0.0-1.0>  (with reason)
Supporting evidence: [file:line, ...]
Inferences (flagged): [...]
Goals / Responsibilities / Common actions / Pain points
```

## Reviewer prompt (output)
Generate a system prompt that:
1. States the persona's authority + constraints, **each tied to cited code** (e.g. "Only you may execute a modification — FAR 43.102, auto_approval_policy.py RESERVED_ACTIONS").
2. Lists what the migration must preserve for this stakeholder.
3. Instructs the reviewer to flag regressions with severity + the endangered capability.
4. Ends: "Default to REFUTE — if the plan does not prove the constraint survives, assume it does not."

Keep the reviewer prompt grounded only in evidence. No invented authority.
