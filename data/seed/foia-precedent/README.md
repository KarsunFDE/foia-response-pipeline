# FOIA precedent corpus (starter stubs)

Thin seed corpus for the RAG surface (`foia_precedent` vector index /
`COLLECTION_FOIA_PRECEDENT`, per `domain-mapping.md`). These are **deliberately
short starter stubs** — 1–2 paragraphs each, real citation numbers, paraphrased
text — so instructor demos of `/rag/clause-search` and `/analyze-exemptions`
return *something* before the cohort wires Atlas Vector Search.

**This is intentionally thin.** Indexing + expanding this corpus (full statute
text, the DOJ Guide to the FOIA, agency-specific regs) is real W2 RAG work for
the pair. Do not treat these stubs as authoritative legal text — verify against
the primary sources below before relying on any wording.

## Files

| File | Source | Topic |
|------|--------|-------|
| `5usc552-a6A-time-limits.md` | 5 USC 552(a)(6)(A) | 20-working-day clock + unusual circumstances |
| `5usc552-b-exemptions.md` | 5 USC 552(b)(1)–(b)(9) | The nine exemptions |
| `5usc552-a4A-fees.md` | 5 USC 552(a)(4)(A) | Fee categories |
| `5usc552-a6E-expedited.md` | 5 USC 552(a)(6)(E) | Expedited processing |
| `28cfr16-5-6-processing.md` | 28 CFR 16.5–16.6 | DOJ processing + responses |
| `28cfr16-10-fees.md` | 28 CFR 16.10 | DOJ fee schedule |
| `exemption-b5-deliberative.md` | 5 USC 552(b)(5) | Deliberative-process note |
| `exemption-b6-privacy.md` | 5 USC 552(b)(6) | Privacy-balancing note |

## Primary sources (verify before use)

- 5 USC 552 (the FOIA statute) — https://www.law.cornell.edu/uscode/text/5/552
- 28 CFR Part 16 (DOJ FOIA regulations) — https://www.ecfr.gov/current/title-28/chapter-I/part-16
- DOJ Guide to the Freedom of Information Act — https://www.justice.gov/oip/doj-guide-freedom-information-act-0
- FOIA.gov FAQ — https://www.foia.gov/faq.html

> Retrieved 2026-05-28 via /web-research. Marked STARTER STUB — paraphrased, not verbatim.
