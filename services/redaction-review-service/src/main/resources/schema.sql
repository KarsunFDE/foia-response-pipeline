-- Relational audit/reporting table for the redaction-review-service search
-- surface (Postgres side; the document store lives on Mongo).
--
-- The SearchRepository issues `SELECT * FROM foiaRequests WHERE status = '...'`.
-- Postgres folds unquoted identifiers to lowercase, so `foiaRequests` resolves
-- to `foiarequests` — created unquoted here so the existing (deliberately
-- vulnerable) query in SearchRepository.searchByStatus works UNCHANGED.
--
-- ⚠ Do NOT "fix" the SearchRepository concat: this table only makes the
--   pair-unique SQL-injection debt (sec-sql-string-concat-aspect-search,
--   OWASP A03) demonstrable. The string-concatenation query is the artifact.
CREATE TABLE IF NOT EXISTS foiaRequests (
    id              VARCHAR(64) PRIMARY KEY,
    tracking_number VARCHAR(64),
    status          VARCHAR(32) NOT NULL,
    requester_type  VARCHAR(48),
    received_date   DATE
);
