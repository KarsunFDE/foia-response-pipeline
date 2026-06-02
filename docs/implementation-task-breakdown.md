# Implementation Task Breakdown

## 1. Goal

- Define actionable Phase 1 implementation tasks for retrieval, grounding, HITL controls, auditability, and evaluation.
- Align work to the brownfield modernization baseline already captured in ADR and retrieval plan.
- Enable parallel execution across teammates with clear ownership boundaries.

## 2. Workstreams

- Corpus ingestion and metadata
- Chunking and indexing
- Hybrid retrieval integration
- Reranking and ranking logic
- Grounding and citation propagation
- HITL gate integration
- Audit logging
- Evaluation and observability

## 3. Task List

### Corpus ingestion and metadata

- Parse FOIA authority set files from `docs/reference/foia/` into a managed ingestion pipeline.
- Extract source metadata: document name, section ID, heading, and raw path.
- Validate ingested corpus records against the reference file set.

### Chunking/indexing

- Define chunk boundaries by FOIA sections/paragraphs and preserve context.
- Create an indexing pipeline that writes chunk metadata and source identifiers.
- Build a reindex command for updated corpus content.

### Hybrid retrieval integration

- Wire LangChain v1.0 to `MongoDBAtlasHybridSearchRetriever`.
- Configure retrieval queries against the FOIA corpus index.
- Verify the retriever returns chunk IDs and source metadata.

### Reranking or ranking logic

- Implement reranking rules using retriever score, citation relevance, and confidence.
- Prioritize exact regulatory phrase matches where available.
- Expose result ranking reasons in retrieval output.

### Grounding/citation propagation

- Attach source identifiers and FOIA references to every retrieved chunk.
- Propagate grounding metadata through recommendation and HITL flows.
- Prevent any evidence output from being returned without source context.

### HITL gate integration

- Add a HITL review gate before any release or recommendation decision.
- Surface retrieval citations, confidence, and grounding details to reviewers.
- Ensure review decisions are recorded and cannot be auto-approved.

### Audit logging

- Log retrieval query inputs, selected citations, and confidence scores.
- Record HITL gate decisions and reviewer identifiers.
- Store audit events in a searchable log format for later review.

### Evaluation and observability

- Track retrieval confidence, result counts, query latency, and hit quality.
- Add instrumentation for failed retrievals and low-confidence escalations.
- Validate retrieval output against representative review scenarios.

## 4. Acceptance Criteria

- Corpus ingestion pipeline exists and ingests `docs/reference/foia/` with source metadata.
- Chunks are indexed with source IDs and preserved FOIA context.
- LangChain v1.0 uses `MongoDBAtlasHybridSearchRetriever` successfully.
- Retrieved results include grounding metadata and citations.
- HITL gate blocks auto-release and logs reviewer actions.
- Observability captures confidence, failures, and citations.

## 5. Dependencies

- `docs/reference/foia/` corpus must be available and parsed.
- MongoDB Atlas Local must be configured for hybrid retrieval.
- LangChain v1.0 integration layer must be available in the service stack.
- HITL workflow and review UI must support citation display.

## 6. Open Questions

- What are the exact document update/reindex triggers for the FOIA corpus?
- How should retrieval confidence thresholds be defined for escalation?
- What review metadata must be stored for downstream audit analysis?
