---
name: fde-evidence-rules
description: Evidence discipline every FDE analysis agent must follow — file:line citations, confidence scores, facts-vs-inferences-vs-recommendations separation, and code-vs-comment tagging. Use during any codebase analysis, persona discovery, or finding extraction.
---

# FDE Evidence Rules

Every finding an analysis agent emits MUST obey these rules. No exceptions.

## 1. Cite file:line for every claim
- Each finding carries `file`, `lineStart`, `lineEnd`.
- No citation → the finding is invalid and must be dropped.
- Quote or paraphrase the supporting line so a reviewer can verify without re-reading.

## 2. Never present assumptions as facts
Tag every finding with one of:
- **fact** — directly observable in code at the cited line.
- **inference** — reasoned from evidence but not stated outright (e.g. "this role is a Contracting Officer" inferred from `co_role` + FAR references).
- **recommendation** — a suggested action; never mix with facts.

The final report separates these into distinct sections.

## 3. Confidence score on every inference
- Range `0.0`–`1.0`.
- `fact` findings default to `1.0`.
- `inference` findings: score by strength + corroboration. Two independent signals agreeing → high. One weak signal → low (flag it).
- State *why* the confidence is what it is.

## 4. Code, not comment
Tag `evidence_type`:
- **code** — the behavior exists in executable code.
- **comment-only** — the claim appears only in comments, docs, or strings.

A "program/feature/persona" supported only by `comment-only` evidence is a **ghost** — report it as "referenced, not implemented," never as real.

## 5. Read before you write
Do not emit a single finding until the assigned file is read in full. No skimming. No guessing about unread regions.

## Finding shape
```
{ claim, file, lineStart, lineEnd,
  type: feature|data|rule|flow|service|debt|security|persona,
  category: fact|inference|recommendation,
  evidence_type: code|comment-only,
  confidence: 0.0-1.0,
  note: "why this confidence / what it means" }
```
