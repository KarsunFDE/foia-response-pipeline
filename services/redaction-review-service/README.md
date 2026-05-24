# redaction-review-service

Spring Boot 3.2. RedactionReview panel coordination. Calls foia-request-service over sync REST.

## Endpoints

| Method | Path | Notes |
|--------|------|-------|
| GET    | `/api/redaction-reviews/{redaction_reviewId}/foia_request/{foia_requestId}` | Fetches foia_request via foia-request-service |
| POST   | `/api/redaction-reviews` | Create panel (⚠ no idempotency key — Item 3) |

## Brownfield-debt items present in this service

- **Item 3** — No Resilience4j circuit breaker / timeout / fallback on `FoiaRequestClient`; no idempotency key on `POST /api/redaction-reviews`.
- **Item 6 (partial)** — Logs `traceId` (third correlation-ID convention).
- **Item 11** — `Dockerfile` uses `:latest`.

See `docs/brownfield-debt.md` for the full inventory.
