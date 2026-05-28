-- Seed rows for the relational `foiaRequests` audit/reporting table.
-- Spans the redaction-review workflow statuses the SearchRepository docstring
-- names: PROPOSED, UNDER_REVIEW, APPROVED_FOR_RELEASE, WITHHELD.
--
-- ON CONFLICT DO NOTHING keeps `spring.sql.init.mode=always` idempotent across
-- restarts (the docker-compose postgres has no volume — Item 11 — so the table
-- is recreated each boot anyway, but this is safe either way).
--
-- These rows make the SQL-injection debt demonstrable: `searchByStatus("' OR
-- '1'='1")` returns all 6 rows (tautology) vs. a single-status match — the
-- W4 OWASP A03 teaching moment.
INSERT INTO foiaRequests (id, tracking_number, status, requester_type, received_date) VALUES
    ('foia-2026-0142', 'DOJ-2026-0142', 'PROPOSED',             'news_media_educational_scientific', '2026-05-14'),
    ('foia-2026-0203', 'DOJ-2026-0203', 'UNDER_REVIEW',         'commercial',                        '2026-05-19'),
    ('foia-2026-0301', 'DOJ-2026-0301', 'UNDER_REVIEW',         'other',                             '2026-05-09'),
    ('foia-2026-0355', 'DOJ-2026-0355', 'APPROVED_FOR_RELEASE', 'news_media_educational_scientific', '2026-05-02'),
    ('foia-2026-0402', 'DOJ-2026-0402', 'WITHHELD',             'commercial',                        '2026-04-28'),
    ('foia-2026-0418', 'DOJ-2026-0418', 'APPROVED_FOR_RELEASE', 'other',                             '2026-05-24')
ON CONFLICT (id) DO NOTHING;
