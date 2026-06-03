# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

Karsun-FDE training project (Cohort #1, Pair 3) modeling a FOIA request processing pipeline with AI-assisted redaction proposals and human-in-the-loop (HITL) review. Brownfield codebase with **intentionally seeded technical debt** (12 baseline + 5 pair-unique items) mechanically locked until scheduled curriculum unlock weeks — do not fix locked debt items unless the unlock week has arrived. `make run-locked-tests` asserts these stay red; fixing them early breaks CI.

## Commands

### Full Stack
```bash
cd infra/docker && docker-compose up --build
```

### Java Services (api-gateway, foia-request-service, redaction-review-service)
Spring Boot 2.7.18 on **Java 11** (`javax.*`, not Jakarta). Run from each service dir.
```bash
mvn -B -DskipTests package                              # build, skip tests
mvn -B test                                             # all tests
mvn -B test -Dtest=FoiaRequestServiceTest               # single class
mvn -B test -Dtest=FoiaRequestServiceTest#shouldRejectHtmlInput   # single method
```

### Python AI Orchestrator
```bash
cd services/ai-orchestrator
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
pytest
pytest tests/test_main.py::test_draft_endpoint          # single test
```

### Angular Frontend
```bash
cd frontend
npm ci
npm start          # dev server :4200
npm test           # Karma unit tests
npm run build      # prod build
```

### Brownfield Debt Verification
```bash
make verify-debt-locks           # full CI debt-enforcement gate (schema + locked tests)
make verify-debt-lockfile-schema # validates docs/debt-lockfile.yml
make run-locked-tests            # all locked-failing tests (MUST stay red)
make check-lint-disabled         # Item 12: GHA lint must remain disabled
make check-dockerfile-latest     # Item 11: Dockerfiles must use :latest
```

## Architecture

Five services over REST; Angular SPA routes through the gateway:

```
Angular :4200
    └─▶ API Gateway :8080 (Spring Cloud Gateway + OAuth2 resource server)
            ├─▶ foia-request-service :8081 (Spring Boot, MongoDB + Postgres)
            │       └─▶ ai-orchestrator :8000 (FastAPI + LangChain + Bedrock)
            └─▶ redaction-review-service :8082 (Spring Boot, MongoDB)
                    └─▶ foia-request-service :8081 (direct — no circuit breaker, Item 3)
```

**Databases:**
- MongoDB — `FoiaRequest`, `RedactionReview`, and inherited-entity documents
- PostgreSQL — audit trail for OIG compliance (⚠ no volume in docker-compose, data lost on restart)

**LLM:** AWS Bedrock `anthropic.claude-3-7-sonnet-20250219-v1:0` via boto3.

**W3C `traceparent` header** propagated across Java services for distributed tracing (correlation IDs are inconsistent — Item 6).

### Key Entry Points

| Service | Entry Point |
|---------|------------|
| API Gateway | `ApiGatewayApplication.java` → `RouteConfig.java`, `SecurityConfig.java` |
| FOIA Request | `FoiaRequestController.java` → `FoiaRequestService.java` → `AuditLogger.java` |
| Redaction Review | `RedactionReviewServiceApplication.java` → `FoiaRequestClient.java`, `AiOrchestratorClient.java` |
| AI Orchestrator | `app/main.py` — many endpoints; FOIA-core: `POST /draft-foia-request` (stub, Item 4), `POST /draft-foia-request-v1` (v1.0 composed-Runnable), `POST /analyze-exemptions`, `POST /agent/intake-triage`, `POST /rag/clause-search` |
| Frontend | `app.routes.ts` → `dashboard`, `foiaRequests`, `redactionReviews` (+ many inherited routes) |

### Inherited Procurement Entities (Not Dead Code)

This repo was mechanically derived from `acquire-gov` (a procurement system) via the `pair-brownfield-generator` skill — see `domain-mapping.md`. The rename rules touched only `FoiaRequest`/`RedactionReview`. **15 procurement entities carried over with live controllers, services, repositories, models, Angular components, and routes**: `Vendor`, `Proposal`, `Amendment`, `Qna`, `Award`, `Contract`, `ContractModification`, `Cpar`, `Finding`, `QaspFinding`, `ClauseLibraryEntry`, `Deliverable`, `DebriefRequest` (plus kept `User`/`AuditEvent`). Surfaces like `vendor-directory`, `cpar-review`, `consensus-ssdd`, `evaluator-workspace`, `award-record`, and orchestrator endpoints `/draft-amendment`, `/answer-qa`, `/eval/*` are this inherited material — **not** FOIA features and **not** accidental leaks. They are intentional raw material (D-059) the pair may repurpose, rename, or delete in W4–W5. `domain-mapping.md` maps each to its FOIA repurpose target (e.g. `Award` → `ReleasePackage`, `Qna` → `RequesterCorrespondence`).

## Brownfield Debt — Do Not Fix Prematurely

Locked items must **stay broken** until their unlock week.

| # | Description | Location | Unlock |
|---|-------------|----------|--------|
| 1 | JWT signature skip on `/api/public/**` | `gateway/SecurityConfig.java`, `JwtSignatureSkipFilter.java` | W4 Wed |
| 2 | Async audit-log race | `audit/AuditLogger.java` | W3/W5 |
| 3 | No circuit breaker (review → request) | `client/FoiaRequestClient.java` | W4 Thu |
| 4 | No structured-output validation | `app/main.py` `/draft-foia-request` stub | W1 Fri |
| 5 | Pre-v1.0 LangChain `LLMChain.run()` | `app/legacy_chain.py` | W2 Mon |
| 6 | Inconsistent correlation IDs | all services | W1/W5 |
| 7 | Unused `pinecone-client` dep | `requirements.txt` | W2 Mon |
| 8 | Frontend hardcodes `:8081` URL | `foia-request-list.component.ts` | W4 Tue |
| 9 | No HTML/OWASP sanitization | `dto/FoiaRequestCreateRequest.java` (`description`) | W4 Wed |
| 10 | No multi-tenant filter on queries | `repository/FoiaRequestRepository.java` | W2 Wed |
| 11 | Dockerfile `:latest` base images | all `Dockerfile`s (ai-orchestrator pinned) | W4 Wed |
| 12 | GHA lint step commented out | `.github/workflows/ci.yml` | W4 Tue |

**Pair-unique locked items** (paths from `domain-mapping.md`):

| id | Location | Unlock |
|----|----------|--------|
| `sec-refresh-token-never-expires` | `gateway/TokenService.java` | W4 |
| `sec-sql-string-concat-aspect-search` | `redactionreview/repository/SearchRepository.java` | W4 |
| `rel-retry-without-backoff` | `redactionreview/client/AiOrchestratorClient.java` (`draft()`) | W5 |
| `obs-error-rethrown-stack-lost` | `ai-orchestrator/app/foia_request_service.py` | W5 |
| `ai-bedrock-no-cost-limit` | `ai-orchestrator/app/cost_guard.py` (no-op stub) | W5 |

⚠ **CI config is duplicated**: `.github/workflows/ci.yml` (the one GitHub Actions actually runs) and `infra/github-actions/ci.yml` (legacy mirror referenced by README/docs) are byte-identical. Item 12 lives in both; keep them in sync.

## Technology Stack Notes

- Java services: Spring Boot **2.7.18** / Java 11 (`javax.*` imports) — intentionally pre-modernization
- Angular: **standalone components**, no NgModules
- LangChain: **0.3.7** — `app/main.py` uses new composed-Runnable style; `legacy_chain.py` uses old `LLMChain(...).run()` (Item 5, keep broken)
- AWS Bedrock: real `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` needed in `.env` for non-stub calls; copy `.env.example` → `.env` first

## Corpus & Domain

FOIA statutory basis: 5 USC 552, 28 CFR 16 (DOJ regs), B1–B9 exemption categories. Seed corpus in `data/seed/foia-precedent/` — uploaded to Atlas Vector Search (index `foia_precedent`) in W2. Workflow stages: intake-triage → exemption-analysis → redaction-proposal → hitl-review → response → appeal.
