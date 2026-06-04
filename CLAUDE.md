# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Training brownfield for the Karsun-FDE 6-week intensive (Cohort #1 Pair 3, `foia-processing` aspect, derived from `acquire-gov`). It ships with **deliberately preserved technical debt**: 12 baseline items (`docs/brownfield-debt.md`) plus 5 pair-unique items (`docs/pair-unique-debt.md`). Each debt item has a scheduled modernization week and a locked-failing test.

**Do NOT fix debt items out of schedule.** Code that "looks broken" (JWT signature skip, SQL string concat, audit-log race, `:latest` Docker tags, commented-out lint in CI, unused `pinecone-client`, missing healthchecks/volumes in docker-compose, etc.) is probably curriculum. Check `docs/brownfield-debt.md` and `docs/debt-lockfile.yml` before touching anything flagged `// ⚠ DELIBERATE — Item N`. CI's `debt-enforcement` job blocks PRs that modernize a locked item without flipping `locked: true → false` in `docs/debt-lockfile.yml` AND the instructor-applied `debt-touch-approved` label.

## Commands

```bash
# Full stack (postgres, mongo, 3 Java services, ai-orchestrator, Angular)
docker-compose -f infra/docker/docker-compose.yml up --build

# Debt enforcement — same checks CI runs; run before pushing
make verify-debt-locks

# Java services (api-gateway, foia-request-service, redaction-review-service)
cd services/<service> && mvn -B test
mvn -B test -Dtest=ClassName          # single test class

# Python (ai-orchestrator)
cd services/ai-orchestrator && pytest tests/
pytest -m "not brownfield_debt"       # exclude locked-failing debt tests (they FAIL by design while debt is in place)
pytest tests/test_foo.py::test_bar    # single test

# ai-orchestrator dev server
cd services/ai-orchestrator
pip install -r requirements.txt -r requirements-test.txt
uvicorn app.main:app --reload --port 8000

# Angular
cd frontend && npm ci && npm run build && npm test

# FOIA corpus indexer (parse + chunk → JSONL; corpus lives in data/seed/foia-precedent/)
python scripts/index-foia-corpus.py
```

CI (`.github/workflows/ci.yml`) builds/tests all 5 services in a matrix. Lint is commented out (deliberate — Item 12). Python tests are not run in CI yet.

## Architecture

Angular SPA (`frontend/`, :4200) → API Gateway (`services/api-gateway/`, Spring Boot 2.7.18 / Java 11 / javax.*, :8080) → two domain services + AI orchestrator:

- `services/foia-request-service/` (:8081) — `FoiaRequest` CRUD; Spring Boot + JPA/Postgres + MongoDB. Package root `com.karsunfde.foiapipeline.foiarequest`.
- `services/redaction-review-service/` (:8082) — `RedactionReview` panel coordination; calls foia-request-service sync REST and ai-orchestrator.
- `services/ai-orchestrator/` (:8000) — Python 3.11 + FastAPI + LangChain v1.0 + Pydantic v2 + boto3/Bedrock. Bedrock calls are currently a stub returning mock JSON. Key modules: `app/main.py` (v1.0 composed-Runnable endpoint), `app/legacy_chain.py` (deliberate pre-v1.0 `LLMChain.run()` — Item 5), `app/atlas_retriever.py` (Atlas hybrid search stub + pymongo lexical fallback; header documents exactly what's missing before real Atlas search works), `app/cost_guard.py` (no-op stub — pair-unique debt).

Datastores: Postgres :5432 (audit/reporting), MongoDB :27017 (documents + future Atlas Vector Search; collection `foia_precedent`).

Agent shape (planned W3): multi-agent redaction proposer + reviewer with HITL interrupt on irreversible release — no auto-release ever. See `docs/hitl-plan.md`, `docs/retrieval-plan.md`, `docs/adrs/`.

Domain corpus: 5 USC 552 / 28 CFR 16 markdown under `data/seed/foia-precedent/` (`docs/reference/foia/` referenced in retrieval-plan.md does not exist yet). `domain-mapping.md` is the rename lookup from the parent `acquire-gov` repo — task specs written against sibling repos translate through it.

## Debt-enforcement mechanics

- `docs/debt-lockfile.yml` — ground truth for lock state. Each item maps to a locked-failing test (pytest marker `brownfield_debt_N` or Java test class) that FAILS while debt exists and PASSES once fixed.
- `.github/scripts/run-locked-tests.sh` asserts locked tests still fail; a locked test passing = accidental modernization = CI failure.
- Legit modernization flow: confirm week is scheduled → flip `locked: false` in lockfile → tick YES branch in PR template with item IDs → instructor applies `debt-touch-approved` label.

## PR requirements

- `pr-summary-check` workflow fails PRs whose `## Summary` section is empty or lacks at least one backtick-quoted `path/to/file` token — list every file touched and why.
- PR template debt checkbox (NO/YES) is mandatory; checked by `.github/scripts/verify-pr-debt-checkbox.py`.
- Branch naming: `<initials>/<short-description>`. Commits: conventional commits; debt fixes MUST use `debt(item-N): ...` prefix.
- Modernization decisions get an ADR under `docs/adrs/` (ADR-0002+).

## Found something broken that isn't inventoried?

Open an issue with the `instructor-review` label — don't fix it. Some gaps (no postgres volume, no healthchecks, stub `deploy.yml`) are intentional reinforcement gaps, not bugs.
