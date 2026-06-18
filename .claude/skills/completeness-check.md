---
name: completeness-check
description: Reconcile the discovered file work-list against the files actually read, and report any gap. Use as the gate before writing the analysis report. Enforces total coverage — no silent truncation.
---

# Completeness Check

The anti-"invisible domain" gate. Guarantees the analysis saw the whole repo, or says exactly what it missed.

## Procedure
1. Take the **work-list** = every source file enumerated by the filesystem walk (discovery phase).
2. Take the **read-set** = every file that produced findings (or was explicitly read and found empty).
3. Compute `missed = work-list − read-set`.

## Report (never silent)
- If `missed` is empty → state "Total coverage: N/N files read."
- If `missed` is non-empty → list every missed file and WHY (skipped, errored, too large, filtered). Then state the coverage fraction.
- A truncation, sampling, or top-N cap MUST be logged here. Silent truncation reads as "covered everything" when it didn't — forbidden.

## Oversized files
If a single file exceeded an agent's context and was chunked, confirm all chunks were read and stitched. If a chunk was dropped, it counts as missed.

## Output
```
Coverage: <read>/<total> files (<pct>%)
Missed: [ {file, reason}, ... ]
Chunked files: [ {file, chunks_read/chunks_total}, ... ]
```
