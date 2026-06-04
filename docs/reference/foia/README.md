# FOIA authority corpus (authoritative — ADR-0003)

This directory is the **managed reference corpus** for the Phase 1 retrieval
baseline, per [ADR-0003](../../adrs/0003-retrieval-baseline.md),
[`docs/retrieval-plan.md`](../../retrieval-plan.md), and
[`docs/implementation-task-breakdown.md`](../../implementation-task-breakdown.md).
Retrieval grounding and audit logs trace back to the files here.

The current contents were **copied from the starter stubs** at
[`data/seed/foia-precedent/`](../../../data/seed/foia-precedent/) on
2026-06-04 to give the pipeline an ADR-aligned corpus home. The seed
directory stays frozen as instructor-demo scaffolding; this directory is the
one that grows. Each stub still carries its `> STARTER STUB` provenance
footer — the indexer strips that footer at parse time, and the footer is the
marker that a file has NOT yet been replaced with verified primary-source
text.

## Corpus rules

- Every file MUST carry YAML frontmatter with at least a `cite` field
  (e.g. `cite: 5 USC 552(b)`); `topic` and `exemption` are optional but
  indexed when present. `far_part` is derived from `cite` ("5 USC 552" or
  "28 CFR 16").
- Files are chunked by the rules in
  [`docs/corpus-chunking-rules.md`](../corpus-chunking-rules.md) — keep
  H2+/bold-label section structure so chunk boundaries stay meaningful.
- Do not paste unverified wording. Replace stub text only with text checked
  against the primary sources below, and remove the `> STARTER STUB` footer
  when you do.
- Any content change requires an explicit reindex:
  `python scripts/index-foia-corpus.py --upsert --yes`.

## W2 expansion checklist (replaces stubs with primary-source text)

| File | Source to verify against |
|------|--------------------------|
| `5usc552-a6A-time-limits.md` | [5 USC 552](https://www.law.cornell.edu/uscode/text/5/552) (a)(6)(A) |
| `5usc552-b-exemptions.md` | [5 USC 552](https://www.law.cornell.edu/uscode/text/5/552) (b)(1)–(b)(9) |
| `5usc552-a4A-fees.md` | [5 USC 552](https://www.law.cornell.edu/uscode/text/5/552) (a)(4)(A) |
| `5usc552-a6E-expedited.md` | [5 USC 552](https://www.law.cornell.edu/uscode/text/5/552) (a)(6)(E) |
| `28cfr16-5-6-processing.md` | [28 CFR Part 16](https://www.ecfr.gov/current/title-28/chapter-I/part-16) §§ 16.5–16.6 |
| `28cfr16-10-fees.md` | [28 CFR Part 16](https://www.ecfr.gov/current/title-28/chapter-I/part-16) § 16.10 |
| `exemption-b5-deliberative.md` | [DOJ Guide to the FOIA](https://www.justice.gov/oip/doj-guide-freedom-information-act-0) — Exemption 5 |
| `exemption-b6-privacy.md` | [DOJ Guide to the FOIA](https://www.justice.gov/oip/doj-guide-freedom-information-act-0) — Exemption 6 |

Additional planned sources: [FOIA.gov FAQ](https://www.foia.gov/faq.html),
agency-specific FOIA regulations as needed.
