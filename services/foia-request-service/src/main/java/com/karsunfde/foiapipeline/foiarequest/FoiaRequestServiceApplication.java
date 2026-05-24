package com.karsunfde.foiapipeline.foiarequest;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * foia-response-pipeline — FoiaRequest Service.
 *
 * FAR/DFARS foiaRequest lifecycle. CRUD over MongoDB; audit-log writes to
 * an audit collection (deliberately written *after* response — see Item 2).
 *
 * DELIBERATE BROWNFIELD DEBT in this service:
 *   - Item 2 — Audit row written after HTTP response is flushed
 *   - Item 6 — Logs correlationId (inconsistent with X-Request-ID / traceId)
 *   - Item 9 — Accepts arbitrary HTML in description (no Jsoup sanitization)
 *   - Item 10 — agency_id in schema but no query filter (no tenant boundary)
 *   - Item 11 — Dockerfile uses :latest
 */
@SpringBootApplication
public class FoiaRequestServiceApplication {
    public static void main(String[] args) {
        SpringApplication.run(FoiaRequestServiceApplication.class, args);
    }
}
