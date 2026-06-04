# FOIA corpus chunking rules

Answers `docs/retrieval-plan.md` open question 15 ("What exact chunk size and
boundary rules should be used for FOIA authority set sections?"). The
implementation is `scripts/index-foia-corpus.py`; this document is the
specification it follows. Tests pinning these rules live in
`services/ai-orchestrator/tests/test_index_foia_corpus.py`.

## Parse stage (per file)

1. **Frontmatter** — leading `---`-delimited YAML block is removed from the
   body and parsed as flat `key: value` metadata (`cite`, `topic`,
   `exemption`). Missing/`null` values become `None`.
2. **Title** — the first H1 (`# ...`) is extracted as `title` and removed
   from the body; it seeds `heading_path`.
3. **Provenance footer** — only trailing lines matching `> STARTER STUB ...`
   (plus surrounding blanks) are stripped. Legitimate trailing blockquotes
   (quoted statutory text) are preserved.

## Boundary rules

1. **Section boundaries** — split at every H2–H6 heading and at every
   line-leading bold label (e.g. `**§ 16.5 (Timing).**`, the 28 CFR inline
   marker style). The heading/label text becomes the section's
   `heading_path` entry; the marker line itself is removed from chunk text.
   Text before the first boundary is its own section with an empty label.
2. **Size budget** — `MAX_SECTION_CHARS = 800`. Sections at or under budget
   are one chunk. Rationale: small enough for precise grounding/citation,
   large enough to preserve regulatory meaning, comfortably inside the
   Titan v2 embedding input budget (ADR-0003).
3. **Paragraph packing** — over-budget sections are split on blank-line
   paragraph boundaries and greedily re-packed into chunks ≤ 800 chars.
4. **Hard split (fallback)** — a single paragraph over budget is split at
   sentence boundaries (`.;:` + whitespace) and packed; a single sentence
   over budget falls back to a character window with
   `CHUNK_OVERLAP_CHARS = 100` overlap between consecutive slices, so a
   clause cut mid-thought stays retrievable from both sides.
   **Invariant: no emitted chunk exceeds 800 chars.**

## Metadata preserved on every chunk

| Field | Meaning |
|-------|---------|
| `clause_id` | filename stem — the citation handle used in synthesis prompts |
| `cite` | frontmatter cite (e.g. `5 USC 552(b)`) |
| `title` | H1 text |
| `heading_path` | breadcrumb `[title, section label]` |
| `far_part` | `"5 USC 552"` / `"28 CFR 16"`, derived from `cite` (exact-match retrieval filter) |
| `source_file` | corpus filename (audit traceability) |
| `chunk_index` | 0-based position within the source file |
| `topic`, `exemption` | frontmatter passthrough |
| `text` | chunk body (no frontmatter, no footer) |
| `run_id`, `indexed_at` | stamped at Mongo load time, identifies the corpus run |

## Validation (ingestion gate)

A corpus run fails (exit 1, nothing written) if any non-skipped corpus file
produces zero chunks, any chunk references a file outside the corpus set, or
any chunk has empty text. Per-file chunk counts are printed on every run.

## Corpus location

Authoritative corpus: `docs/reference/foia/` (ADR-0003). The starter stubs
at `data/seed/foia-precedent/` are frozen instructor-demo scaffolding —
override with `--corpus-dir` only for demo purposes.
