# ADR 0004 — Lexical-first retrieval; Atlas hybrid behind an explicit enable flag

Status: Accepted
Date: 2026-06-08

## Context

ADR 0003 sets the Phase 1 *target*: an Atlas hybrid retriever (Titan v2 @ 512
dims) over the managed FOIA corpus. That target is not yet live. As implemented
in `services/ai-orchestrator/app/atlas_retriever.py`:

- `_atlas_hybrid_search()` is still a stub — the real `MongoDBAtlasVectorSearch`
  wiring, the Atlas vector index, and an embedding-bearing corpus do not exist
  yet. Several prerequisites are outstanding (see *Conditions to enable hybrid*).
- The working retrieval path today is pymongo `$text` lexical search over the
  `foia_precedent` collection.
- `langchain-mongodb==0.11.0` is listed in `requirements.txt`, so the import
  guard `_LANGCHAIN_MONGODB_AVAILABLE` evaluates **True** in any normal install.

This creates a sharp risk: if routing keyed on import availability alone,
`langchain-mongodb` being installed would silently route live FOIA queries into
the unwired hybrid stub, which returns `[]`. That is a silent retrieval
blackout on a system bound by 5 U.S.C. 552 / 28 CFR 16 — the worst failure mode
(it looks like "no responsive precedent" rather than "retrieval is broken").

The rationale for the chosen guard currently lives only in module docstrings
(`atlas_retriever.py` header and the `ATLAS_HYBRID_ENABLED` comment). CLAUDE.md
requires durable architecture decisions to be recorded as an ADR. This ADR
records it.

## Decision

1. **Lexical `$text` is the only live retrieval path for now.** `clause_search`
   serves results from `_pymongo_text_search` until the hybrid path is wired,
   indexed, and tested.

2. **The Atlas hybrid path is gated behind an explicit `ATLAS_HYBRID_ENABLED`
   env flag, AND import availability — not import availability alone.** Routing
   to `_atlas_hybrid_search` requires both `ATLAS_HYBRID_ENABLED` truthy *and*
   `_LANGCHAIN_MONGODB_AVAILABLE`. Installing `langchain-mongodb` can never, on
   its own, divert traffic from the working lexical path to the unwired stub.

3. **The lexical path is treated as uncalibrated.** Mongo `$text` score is not
   normalized confidence, so the lexical path applies no absolute score floor;
   it returns ranked top-k and the endpoint forces mandatory human review of any
   synthesis (`atlas_retriever.lexical_path_active()` → `needs_review=True`).
   The absolute `MIN_SCORE` floor applies only on the calibrated hybrid path.
   (See the `fix(retrieval): replace uncalibrated MIN_SCORE cut …` change.)

## Rationale

- A live, grounded, auditable retrieval path is needed now; the lexical path
  delivers that while the hybrid path is built out, without blocking downstream
  drafting/HITL work.
- An explicit enable flag makes the cutover a deliberate, reviewable act rather
  than an accident of dependency resolution. The failure mode it prevents
  (silent routing to an empty stub) is both easy to trigger — a single line in
  `requirements.txt` — and dangerous, because empty retrieval is
  indistinguishable from "no responsive precedent" to callers.
- Mandatory review on the lexical path keeps Phase 1 FOIA-conservative: nothing
  uncalibrated is presented as authoritative without a human reviewer.

## Conditions to enable hybrid

Flip `ATLAS_HYBRID_ENABLED=true` only after ALL of the following hold (the W2
TODO block at the top of `atlas_retriever.py` is the authoritative checklist):

1. `langchain-mongodb` installed (already in `requirements.txt`).
2. `MONGO_DB` env var present for `ai-orchestrator` in
   `infra/docker/docker-compose.yml`.
3. Atlas Search vector index `foia_precedent_vector` created on the
   `foia_precedent` collection (knnVector, 512 dims, cosine).
4. Corpus indexed *with embeddings* (Titan v2) via `scripts/index-foia-corpus.py`.
5. `_atlas_hybrid_search()` stub body replaced with real
   `MongoDBAtlasVectorSearch` wiring **and** covered by tests.
6. `scripts/eval-retrieval-quality.py` run against the hybrid path with
   hit@5 at or above the agreed floor.

## Consequences

- Default deployments run lexical-only; all lexical synthesis is gated behind
  human review. Reviewers will see `needs_review=True` on every lexical-path
  response by design until hybrid is enabled.
- The hybrid path can be wired and merged incrementally without changing
  production behavior, since it stays dormant until the flag is set.
- The enable/disable decision is a runtime env change, not a code change —
  consistent with ADR 0003's "technology lift, not design pivot" stance.

## Rollback criteria

- To roll back from hybrid to lexical: unset / set `ATLAS_HYBRID_ENABLED=false`.
  No deploy required.
- Roll back automatically-by-policy if, after enabling hybrid, any of:
  - `_atlas_hybrid_search` raises `RetrievalUnavailableError` in normal
    operation (infra/index not actually ready), or
  - `eval-retrieval-quality.py` hit@5 regresses below the lexical baseline,
  - then disable the flag and return to lexical + mandatory review while the
    hybrid path is fixed.

## Alternatives Considered

1. **Route on import availability alone** (no flag). Rejected — installing
   `langchain-mongodb` would silently route live queries into the unwired stub
   returning `[]`, a silent retrieval blackout.
2. **Delete/skip the hybrid stub until fully wired.** Rejected — keeping the
   stub + flag lets the hybrid path be built and reviewed incrementally and
   documents the intended target in code.
3. **Apply an absolute score floor on the lexical path.** Rejected — `$text`
   scores are uncalibrated; see ADR rationale and the retrieval-gating change.

## Follow-up Work

- Complete the *Conditions to enable hybrid* checklist (tracks the W2 RAG work).
- Calibrate a hybrid-path `MIN_SCORE` from the gold set once the hybrid path is
  live (the lexical path intentionally has no floor).
