# ADR 0003 — Retrieval Baseline for Phase 1

Status: Proposed
Date: 2025-06-01

## Context

This repo is a Phase 1 brownfield modernization of the FOIA response pipeline. The first retrieval baseline must be practical, grounded, auditable, and human-in-the-loop rather than a perfect long-term architecture.

The source corpus is managed locally from FAR XML under `docs/reference/far/`. Phase 1 development uses MongoDB Atlas Local, with the expectation that Atlas Cloud will be adopted later for production-scale retrieval.

LangChain v1.0 is the integration layer. The system needs a retriever that supports hybrid search quality and explicit grounding / citation behavior for auditability.

## Decision

- Use `MongoDBAtlasHybridSearchRetriever` as the Phase 1 baseline retriever.
- Use Titan v2 embeddings at 512 dimensions as the embedding baseline.
- Keep source documents as a managed local reference corpus derived from FAR XML in `docs/reference/far/`.
- Start with MongoDB Atlas Local for development, and plan a migration path to MongoDB Atlas Cloud later.
- Carry grounding, citations, and auditability forward into downstream recommendation and HITL steps.

## Rationale

Hybrid retrieval provides a practical balance between semantic recall and exact-match grounding for regulatory/legal content in the FAR corpus. It is a stronger baseline than pure sparse or pure dense retrieval, while still fitting the current LangChain v1.0 and Atlas tooling.

Titan v2 at 512 dims is a reasonable embedding baseline for Phase 1 because it is specific, compact, and matches the project’s current model expectations without inventing a more advanced or unvalidated embedding scheme.

A local managed corpus keeps control over the source material and avoids premature dependence on external document stores. The FAR XML corpus under `docs/reference/far/` is the authoritative reference for grounding and audit logs.

Using Atlas Local now enables fast developer iteration while preserving the same Atlas-compatible retrieval approach for a later Cloud Atlas rollout.

## Consequences

- The Phase 1 retrieval pipeline is anchored to a hybrid Atlas retriever and embedder baseline rather than a custom or experimental retrieval architecture.
- The repo’s reference data remains explicit and auditable in `docs/reference/far/`, simplifying traceability from output to source document.
- Downstream recommendation, redaction, and HITL workflows must retain grounding/citation metadata from the retriever output.
- Migration to Atlas Cloud later will be a technology lift rather than a design pivot, since the same retrieval pattern is already in place.

## Alternatives Considered

1. Pure sparse retrieval over FAR XML. Rejected because it would lose semantic recall and make grounding-only behavior harder to support across the legal corpus.
2. Pure dense retrieval with a different embedding model. Rejected because it would reduce auditability and introduce a less practical baseline for Phase 1.
3. External managed reference store instead of a local corpus. Rejected for Phase 1 because a local managed FAR XML corpus is simpler to control and easier to audit during early brownfield modernization.

## Follow-up Work

- Define the exact `MongoDBAtlasHybridSearchRetriever` configuration in the service implementation.
- Document the Atlas Local to Atlas Cloud migration path and any Cloud-specific security/access settings.
- Ensure retriever output includes citations and source identifiers that are surfaced through downstream HITL and recommendation flows.
