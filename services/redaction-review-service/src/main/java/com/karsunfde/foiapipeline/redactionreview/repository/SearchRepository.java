package com.karsunfde.foiapipeline.redactionreview.repository;

import com.karsunfde.foiapipeline.redactionreview.model.RedactionReview;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Repository;

import javax.annotation.Nullable;
import java.util.List;

/**
 * ⚠ DELIBERATE PAIR-UNIQUE BROWNFIELD DEBT — sec-sql-string-concat-aspect-search ⚠
 *
 * Per D-059 Cohort #1 Pair 3 (foia-response-pipeline) injection from
 * skills/pair-brownfield-generator/references/pair-unique-debt-pool.yml.
 *
 * <p>This repository exposes a SQL search surface over the {@code foia_requests}
 * audit-and-reporting table (Postgres side; the document store on the Mongo
 * side is unaffected). Search-by-status is implemented via raw string
 * concatenation — classic OWASP A03 Injection.</p>
 *
 * <p><b>Why JDBC + Postgres in a Mongo-primary service:</b> federal-acquisitions
 * deployments routinely use Postgres for the audit/reporting flat-projection
 * alongside Mongo for the document store. The bug lives on the relational
 * search path because that's where ad-hoc search queries usually grow.</p>
 *
 * <p>Cohort finds this in W4 (AI Security Engineering — OWASP A03 Injection
 * day) by passing {@code searchByStatus("' OR '1'='1")} and watching every
 * row come back.</p>
 *
 * <p><b>FOIA-domain context:</b> the {@code status} dimension on a
 * {@link RedactionReview} is the FOIA Officer's view of where each
 * proposed redaction is in the workflow (e.g., {@code PROPOSED}, {@code
 * UNDER_REVIEW}, {@code APPROVED_FOR_RELEASE}, {@code WITHHELD}). An
 * injection on this endpoint lets an adversarial requester or compromised
 * portal user enumerate every redaction state — including pending
 * release decisions on other requesters' responsive pages — bypassing
 * the per-requester ACL the Mongo layer enforces.</p>
 */
@Repository
public class SearchRepository {

    private final JdbcTemplate jdbc;

    public SearchRepository(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    private static final RowMapper<RedactionReview> MAPPER = (rs, n) -> {
        RedactionReview r = new RedactionReview();
        try { r.setId(rs.getString("id")); } catch (Exception ignored) {}
        return r;
    };

    /**
     * Search redaction-review rows by status.
     *
     * <p>⚠ Bug: status value is concatenated directly into the SQL string.
     * {@code searchByStatus("' OR '1'='1")} returns every row.</p>
     */
    public List<RedactionReview> searchByStatus(@Nullable String status) {
        // ⚠ pair-unique debt sec-sql-string-concat-aspect-search:
        // classic concat — `status=' OR '1'='1` injects.
        String sql = "SELECT * FROM foia_requests WHERE status = '" + status + "'";
        return jdbc.query(sql, MAPPER);
    }

    /**
     * Returns the total row count — used by the locked-failing test to
     * detect injection (injected.size() < total means the WHERE was
     * actually restrictive; injected.size() == total means '1'='1' was
     * tautological).
     */
    public int totalCount() {
        Integer n = jdbc.queryForObject("SELECT COUNT(*) FROM foia_requests", Integer.class);
        return n == null ? 0 : n;
    }
}
