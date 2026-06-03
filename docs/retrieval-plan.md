# Retrieval Plan

## 1. Purpose

Define the Phase 1 retrieval approach for the FOIA response pipeline. The plan anchors the system on LangChain v1.0, MongoDB Atlas Local for development, and a grounded, auditable retrieval workflow.

## 2. Scope

- Retrieval for retrieval-relevant reference content derived from FOIA authority sources.
- Baseline search and evidence delivery for recommendation, redaction, and HITL review flows.
- Support for citations, confidence, escalation, and later migration to Atlas Cloud.

## 3. Constraints and Assumptions

- Phase 1 is brownfield modernization, not final architecture.
- LangChain v1.0 is the integration layer.
- Atlas Local is the development target; Atlas Cloud is the future target.
- No auto-release behavior: human review is required before any response decision.
- Corpus is static, authoritative FOIA authority set under `docs/reference/foia/`.

## 4. Baseline Architecture Decisions

- Use `MongoDBAtlasHybridSearchRetriever` as the baseline retriever.
- Use Titan v2 embeddings at 512 dimensions.
- Store source corpus as managed local reference data, not an external transient store.
- Preserve grounding metadata through downstream recommendation and HITL stages.

## 5. Corpus Boundaries and Metadata

- Corpus boundaries are the FOIA authority set files in `docs/reference/foia/`.
- Metadata includes document source, section identifiers, and any parsed FOIA headings.
- Reference corpus is read-only for retrieval and auditability.
- Any document updates must be tracked and reindexed explicitly.

## 6. Chunking Strategy

- Chunk by logical FOIA section or paragraph boundaries, preserving regulatory context.
- Keep chunks small enough for precise grounding but large enough to preserve meaning.
- Include source identifiers and chunk positions in each indexed record.

## 7. Retrieval Strategy

- Use hybrid retrieval to combine semantic and exact-match signals.
- Query the Atlas Hybrid Search retriever against the FOIA corpus.
- Prefer retriever output that includes document source and chunk-level identifiers.

## 8. Reranking Strategy

- Apply reranking based on retriever score, citation relevance, and retrieval confidence.
- Prioritize chunks with exact matching regulatory phrases and semantic relevance.
- Surface top results with clear indication of why they were selected.

## 9. Grounding and Citation Requirements

- Every retrieved item must include a source identifier and the original FOIA reference.
- Grounding metadata must be available to HITL reviewers and audit logs.
- Do not return ungrounded or hallucinated content as evidence.

## 10. Failure Handling and Escalation

- If retrieval confidence is low, escalate to a human reviewer rather than auto-release.
- If no strong matches are found, return a safe fallback that says the system could not confidently answer from the corpus.
- Log retrieval failures, low-confidence queries, and missing source matches for follow-up.

## 11. Security and Access Control

- Restrict retrieval access to the service runtime and authorized review workflows.
- Keep the FOIA reference corpus under repo-managed control; do not expose raw corpus paths to end users.
- Ensure any Atlas credentials used for Local or Cloud access are stored securely.

## 12. Observability and Evaluation

- Track retrieval confidence, result counts, and query latency.
- Log citations returned for each recommendation and review action.
- Evaluate quality against representative retrieval scenarios and FOIA lookup expectations.

## 13. Implementation Task Breakdown

- Configure LangChain v1.0 with `MongoDBAtlasHybridSearchRetriever`.
- Build the indexing process for FOIA under `docs/reference/foia/`.
- Implement Titan v2 512-d embedding generation.
- Add citation and grounding metadata to indexed chunks.
- Wire retrieval results into HITL and recommendation flows.
- Add logging for confidence, failures, and source citations.

## 14. Acceptance Criteria

- Retrieval uses `MongoDBAtlasHybridSearchRetriever` and Titan v2 512-d embeddings.
- Source corpus is derived from `docs/reference/foia/` and returns chunk-level citations.
- Low-confidence queries trigger escalation, not auto-release.
- Logs capture retrieval confidence, citations, and failure conditions.

## 15. Open Questions

- What exact chunk size and boundary rules should be used for FOIA authority set sections?
- How will Atlas Cloud schema/config differ from Atlas Local for hybrid retrieval?
- What cadence will the reference corpus be updated and reindexed?
