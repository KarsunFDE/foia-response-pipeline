# Stretch Backlog — foia-response-pipeline

> Aspirational work items. Pair may pursue any of these for differentiation
> credit in W3+W6 retro. **Not assessed** — rubric does NOT penalize pairs
> who skip the backlog. Items are defendable on the merits (architecture +
> reasoning) even if unbuilt.
>
> Authored by `pair-brownfield-generator` on 2026-05-24 per D-059. Selected
> from `fde-10-week/skills/pair-brownfield-generator/references/stretch-backlog-pool.yml`
> recipe `cohort_1_pair_3_foia` (5 items in recipe — 4 selected for this
> pair, spanning all 4 categories: capability, architecture, performance,
> governance). The deselected fifth item (`gov-aspect-changelog-from-audit`)
> is documented at the end for transparency.

## Items (4 total)

### cap-aspect-mobile-friendly-public — Mobile-friendly public-facing FOIA request submission

**Category:** capability
**Difficulty:** modest
**Aspect fit:** foia-processing — FOIA.gov serves a mobile-heavy public; citizens / journalists submit from phones

Build a responsive public view (PWA-style) for the FoiaRequest submission and
status-check surface. Real users on phones is real federal-system reality —
Section 508 / WCAG 2.1 AA targets. FOIA in particular has a strong citizen-on-mobile
profile (journalist filing from a presser, citizen filing from home).

**Why this would be defendable in W3+W6 retro:**

Accessibility is non-negotiable for federal systems. Even partial build
demonstrates 508 awareness. FOIA's public-citizen-facing surface makes this a
real differentiator versus Pair 1 (peer-review portal — internal users) and
Pair 2 (contract-payment — government / vendor users). Defendable as
"FOIA.gov + agency portals run as PWAs in 2026."

---

### gov-aspect-data-retention-policy — Data-retention policy enforcement (FedRAMP MP-6 / NARA schedules)

**Category:** governance
**Difficulty:** substantial
**Aspect fit:** foia-processing — FOIA records carry NARA-mandated retention; appeals + litigation pull on this

Implement automated retention enforcement: FoiaRequests, ResponsivePages,
ExemptionDeterminations, and audit logs tagged with NARA retention schedule
(common schedules: 2 years for routine requests; 6 years for litigation-hold
requests; permanent for landmark precedent). Daily job archives then deletes
per schedule.

**Why this would be defendable in W3+W6 retro:**

OIG audit reality — pairs who build it have FedRAMP MP-6 evidence ready.
FOIA-specific angle: 5 USC 552(a)(4)(A)(ii) requires fee schedules and request
records be retained; agency record schedules per 44 USC 33 set the bar. Even
ADR-only is W6-defendable. Pair has a strong cross-link to Pair 1's
audit-trail work + Pair 2's closeout-service.

---

### perf-aspect-search-pgvector — Migrate FoiaRequest precedent search from Mongo Atlas to Postgres pgvector

**Category:** performance
**Difficulty:** substantial
**Aspect fit:** any — but FOIA's RAG-over-precedent use case is a clean side-by-side fit

Exercise the "which vector store" decision concretely. Implement pgvector
alongside Atlas, run side-by-side eval (recall@10, p95 latency, cost). Cohort
defends the kept-vs-replaced call. FOIA's precedent corpus (prior agency
responses, exemption case law, OIP guidance) is dense + slow-moving — ideal
for a controlled comparison.

**Why this would be defendable in W3+W6 retro:**

W2 scenario-alternatives prompt mirrors this. Pairs who build side-by-side
eval have real numbers (recall@10, p95 latency, cost-per-1k-queries) for W6
client showcase. Defendable even if you decide "stay on Atlas" — the
methodology + numbers are the deliverable.

---

### arch-cqrs-aspect-projections — CQRS — separate write-side FoiaRequest from read-side projections

**Category:** architecture
**Difficulty:** ambitious
**Aspect fit:** foia-processing — FOIA dashboards (timeline-tracker, statutory-miss alerts) are natural projection consumers

Write-side accepts FoiaRequest mutations (intake, exemption-decision,
release-decision); projection workers fan out read-optimized views — FOIA
dashboard (open requests by office, statutory clock per request), search
index, audit-report flat table, OIP quarterly-statistics projection.
Exercises eventual consistency + read/write asymmetry reasoning.

**Why this would be defendable in W3+W6 retro:**

Defendable as "premature for current load, but here's the inflection point +
projection-worker design." Pairs who DO build it get extra retro discussion
time. FOIA-specific angle: the timeline-tracker projection naturally needs to
re-read all open requests on every clock-tick, which is the cleanest
motivating example for read/write separation in this codebase.

---

## Deselected from this pair's recipe

- **gov-aspect-changelog-from-audit** (governance, modest) — auto-generate
  FoiaRequest changelog from audit-log stream. Deselected because the
  `stretch_backlog_count: 4` input + the breadth-across-categories goal led
  to picking only one governance item (data-retention is the higher-stakes
  FOIA pick). Pair may opt-in if they finish a category before W6 — it's a
  natural "additional governance polish" extension of the audit-trail work
  they'll do anyway.

## Cross-pair note

Other pairs in this cohort have different stretch backlogs — overlap is
allowed (these items are aspirational), but each pair's set is curated to
their aspect's fit. See:

- `grants-portal-modern/BACKLOG.md` — Pair 1 (grants-management)
- `contract-payment-flow/BACKLOG.md` — Pair 2 (post-award-contract-administration)

W3+W6 cross-pair retro includes a "did any pair pursue a stretch item, and
what did they learn?" prompt.
