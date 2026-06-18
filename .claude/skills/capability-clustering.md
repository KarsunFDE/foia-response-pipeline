---
name: capability-clustering
description: Group raw analysis findings into business-capability clusters, detect duplication across files, demote ghosts, and score criticality. Use during the merge phase after findings from all files are collected. Cross-checks clusters against directory structure.
---

# Capability Clustering

Turns a flat list of cited findings into business capabilities — the unit modernization scopes against.

## 1. Group by domain capability
Cluster findings by the business capability they serve (e.g. Contract Modification, Payment Certification, Audit/Compliance, Contract Lookup), NOT merely by directory. A capability spread across several dirs is ONE capability.
- Cross-check each cluster against directory structure as a sanity signal, not the grouping key.

## 2. Detect duplication
If the same logic/feature appears in multiple places, record it once with `duplicated_at: [file:line, ...]`. Never count copies as distinct capabilities.

## 3. Demote ghosts
Any finding whose evidence is `comment-only` → exclude from real capabilities; list separately under "referenced, not implemented."

## 4. Per-capability record
```
Capability: <name>
Description
Supporting services / data / workflows  (cited)
Users (personas)
Business value
Criticality: Critical | High | Medium | Low
What breaks if removed
Confidence
```

## 5. Criticality guidance
- **Critical** — irreversible / money / legal authority / audit (e.g. modification execution, payment certification).
- **High** — core user workflow.
- **Medium** — supporting.
- **Low** — peripheral / cosmetic.
