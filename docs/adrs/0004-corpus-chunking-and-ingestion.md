# ADR 0004 — Corpus Chunking, Ingestion & Index Schema (Statutory Authority)

Status: Proposed
Date: 2026-06-03
Decision-makers: Pair 3
Supersedes (in part): ADR 0003 §corpus-location (corrects the corpus path)
Related: ADR 0003 (retrieval baseline), proposed ADR 0005 (two-corpus split), proposed ADR 0006 (citation/grounding contract)

## Context

ADR 0003 fixed the *retriever* (`MongoDBAtlasHybridSearchRetriever`), the *embedder* (Titan v2 @ 512 dims), and the *store* (Atlas Local → Cloud). It explicitly deferred "the exact retriever configuration" and how source documents become indexed units. That gap is build-blocking: chunk granularity and chunk metadata determine grounding precision (G2), citation/audit reconstructability (G4), and what every downstream HITL gate and eval can assert. This ADR closes PRD §11 "chunking" for the **statutory-authority corpus only**.

**Scope boundary.** This ADR covers the statutory-authority corpus — 5 USC 552 and 28 CFR 16 — feeding HITL-plan step 3 (retrieve relevant federal FOIA authority + likely exemption categories). The **synthetic prior-decision / precedent corpus** (HITL-plan step 5) and the question of one index vs. two are deferred to ADR 0005. Authority records are agency-neutral public law and carry no tenant scoping; the multi-tenant isolation question (REQ-RAG-3) lives with the precedent corpus and is owned by a later ADR.

**Current corpus state.** The corpus today is a deliberately thin set of starter stubs (1–2 paragraphs each, paraphrased, `STARTER STUB` status) carrying YAML frontmatter (`cite`, `topic`, `exemption`, `status`, `last_verified`). Expanding it to full statute text + the DOJ Guide to the FOIA is real W2 work. The chunking/ingestion design must hold from "thin stubs" through "full statute text" without a redesign.

**Path correction.** ADR 0003 references the corpus at `docs/reference/foia/`, but the seed files currently live at `data/seed/foia-precedent/`. This ADR adopts `docs/reference/foia/` as the canonical authority-corpus location (matching 0003) and treats relocating the existing files there as ingestion follow-up work. The `foia_precedent` Atlas index name / `COLLECTION_FOIA_PRECEDENT` collection from `domain-mapping.md` are unchanged — only the on-disk source path is canonicalised.

## Decision

### 1. Chunking — structure / heading-aware

Chunk on the document's own semantic structure, not a fixed-size window:

- **One chunk per smallest citable unit.** For the exemptions file, that is one chunk per `(b)(x)` exemption — `(b)(1)` … `(b)(9)` each become a discrete chunk so a retrieval can ground to the *exact* exemption it flags. For section-oriented files (time limits, fees, processing), chunk per markdown heading / regulatory subsection.
- **Frontmatter is promoted to chunk metadata**, not embedded in chunk text.
- **No semantic unit is split mid-clause.** A unit that exceeds the embedding input budget is split on sentence/paragraph boundaries with a small overlap, and every resulting sub-chunk inherits the parent's `cite` + metadata.
- **Cross-cutting standards travel with the chunk where relevant.** The foreseeable-harm standard and segregability notes are attached to (or duplicated into) the exemption chunks they govern, so a flagged exemption retrieves its harm/segregability context together (HITL recommendation requirements: cited basis + foreseeable-harm + segregability).

### 2. Per-chunk metadata schema

Every indexed chunk carries:

| Field | Source | Purpose |
|-------|--------|---------|
| `chunk_id` | deterministic — `source_path` + heading anchor + sub-index | Stable across re-ingest; idempotent upsert; audit replay key |
| `text` | chunk body | Embedded + full-text indexed |
| `embedding` | Titan v2 @ 512 dims (ADR 0003) | Dense vector field |
| `cite` | frontmatter `cite` | Citation surfaced to officer + audit (e.g. `5 USC 552(b)(6)`) |
| `exemption` | frontmatter `exemption` | Filter/group by `(b)(x)`; `all`/null for non-exemption docs |
| `topic` | frontmatter `topic` | Coarse routing/filter |
| `authority_type` | derived from cite | `statute` (5 USC 552) vs `regulation` (28 CFR 16) |
| `source_url` | README primary-source table | Audit trail back to primary source |
| `corpus_version` | ingestion run | Snapshot identity for HITL replay (see §3) |
| `last_verified` | frontmatter `last_verified` | Staleness signal |
| `status` | frontmatter `status` | Flags `STARTER STUB` vs verified text |

### 3. Versioning & reproducibility

- Each ingestion run stamps every chunk with a `corpus_version` (monotonic / content-hash-derived). A recommendation's audit record (ADR 0006 / 0009) can then bind to the exact corpus snapshot the retrieval saw — satisfying the HITL-plan "approved snapshot and prompt version" replay requirement (steps 6, 8) and G4 auditability.
- Re-ingestion is an **idempotent upsert keyed on `chunk_id`**: unchanged chunks keep their identity, changed chunks bump `corpus_version`. Re-indexing the corpus must not silently invalidate in-flight HITL reviews pinned to an older snapshot.

### 4. Index field mapping

The Atlas index backs the 0003 hybrid retriever: a `knnVector` field (`embedding`, 512 dims, cosine) for dense recall **and** a full-text index over `text` for sparse/exact-match grounding, with `cite`, `exemption`, `authority_type`, and `corpus_version` as filterable fields. Exact mapping is ingestion follow-up.

## Rationale

- **Legal text is citation-shaped.** Officers and OIP/OIG reason in units of "(b)(6)" or "§ 16.5", not arbitrary token windows. Chunking on those units makes every grounded flag trace to one citable authority and keeps a fixed-size splitter from cutting an exemption mid-clause — directly serving G2 (grounded) and the "grounded or withheld" principle.
- **Metadata-as-fields, not prose.** Promoting frontmatter to filterable fields lets retrieval pre-filter by exemption/authority and lets audit reconstruct source without re-parsing chunk text.
- **Versioned snapshots are the audit substrate.** The HITL loop can pause for days inside the 20-working-day clock; without a pinned `corpus_version`, a mid-review re-index would change what "the system saw," breaking replay.
- **Holds from stubs to full text.** Whole-file chunking is trivial today but breaks when W2 expands files past the embedding input budget; heading-aware chunking scales without a redesign.

## Consequences

- Ingestion gains real logic (heading parsing, frontmatter promotion, deterministic IDs, oversize-unit splitting) rather than a one-line splitter call.
- Corpus authoring conventions become load-bearing: frontmatter completeness and consistent heading structure are now contracts the ingestion (and its tests) depend on.
- Downstream (ADR 0006 citation contract, 0009 eval) can assume every retrieved chunk carries `cite` + `corpus_version` + `exemption` — they build on this schema.
- The corpus must be relocated from `data/seed/foia-precedent/` to `docs/reference/foia/`; references in 0003, `domain-mapping.md`, and any loader config must be updated in the same change.

## Testing assumptions

Per project guideline, implementation lands with verification. The ingestion test suite is expected to assert at minimum:

- **Granularity** — the exemptions file yields exactly nine `(b)(x)` chunks; each `cite` is unique and well-formed.
- **Metadata completeness** — every chunk has non-empty `chunk_id`, `cite`, `corpus_version`; `exemption` matches an allowed value.
- **Size bound** — no chunk's `text` exceeds the Titan v2 input budget.
- **Determinism / idempotency** — re-ingesting unchanged source produces identical `chunk_id`s and no spurious `corpus_version` churn.
- **Citation round-trip** — a chunk's `cite` + `source_url` resolve back to the source file it came from (audit reconstructability).

## Alternatives Considered

1. **Fixed-size window + overlap (recursive splitter).** Rejected: generic and simple, but risks splitting a single exemption mid-clause and weakens citation precision — the opposite of what a withhold-by-default legal corpus needs.
2. **Whole-file, one chunk per document.** Rejected: trivial for today's stubs but breaks the moment W2 expands a file past the embedding input budget; would force a redesign mid-phase.
3. **Both corpora in this ADR.** Rejected: precedent retrieval has a different query intent and a tenant-isolation requirement (REQ-RAG-3); folding it in here would pre-decide the two-corpus topology that ADR 0005 should own.

## Follow-up Work

- Relocate corpus to `docs/reference/foia/`; update 0003, `domain-mapping.md`, and loader config; note the path correction in 0003.
- Implement the heading-aware chunker + frontmatter→metadata promotion + deterministic `chunk_id`.
- Define the concrete Atlas index JSON (vector + full-text + filter fields).
- Specify the `corpus_version` scheme (content hash vs. run stamp) and the re-index-without-breaking-in-flight-reviews procedure.
- Hand the chunk metadata schema to ADR 0006 (citation/grounding contract) as the upstream contract.

## Questions still open (for planning)

- **Titan v2 input budget vs. expanded statute text.** 512 is the *embedding dimension*, not the input limit — but once W2 swaps stubs for full statute text, some subsections may need sub-splitting. What overlap, and does a sub-split exemption still ground cleanly to one `cite`?
- **Cross-references.** FOIA sections cite each other (e.g. (b)(3) "another statute"; segregability spans exemptions). Do we duplicate shared standards into each governed chunk, or add a `related_cites` metadata edge?
- **`exemption` cardinality.** Some chunks govern one `(b)(x)`; others (foreseeable harm, segregability) govern all. Single value, list, or a separate `applies_to_exemptions` field?
- **Stub vs. verified gating.** Should `status: STARTER STUB` chunks be flagged (or down-weighted) at retrieval time so a demo answer is never mistaken for verified authority?
- **Sparse-side tokenization.** The hybrid retriever's full-text half needs an analyzer; legal citations (`552(b)(6)`) tokenize badly under default analyzers — does grounding need a citation-aware analyzer or synonym map?
