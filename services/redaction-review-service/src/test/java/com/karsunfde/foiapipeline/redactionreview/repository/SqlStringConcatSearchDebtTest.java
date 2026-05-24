package com.karsunfde.foiapipeline.redactionreview.repository;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.embedded.EmbeddedDatabase;
import org.springframework.jdbc.datasource.embedded.EmbeddedDatabaseBuilder;
import org.springframework.jdbc.datasource.embedded.EmbeddedDatabaseType;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Locked-failing test for pair-unique debt item sec-sql-string-concat-aspect-search
 * (D-059, Cohort #1 Pair 3 — foia-response-pipeline).
 *
 * <p>Convention: assertion = what-true-after-modernization.</p>
 *
 * <p>While debt is locked (current state): {@link SearchRepository#searchByStatus(String)}
 * concatenates the {@code status} argument directly into the SQL string.
 * Passing {@code "' OR '1'='1"} as status returns every row → detection
 * is {@code injected.size() == total}.</p>
 *
 * <p>After W4 fix:</p>
 * <ul>
 *   <li>Repository uses {@code jdbc.query("... WHERE status = ?", new Object[]{status}, ...)}</li>
 *   <li>The injection string is treated as a literal status value (no rows match)</li>
 *   <li>Test PASSES (injected.size() &lt; total).</li>
 * </ul>
 *
 * <p>FOIA-domain rationale: status enumeration on the redaction-review table
 * would expose every pending release decision across requesters, bypassing
 * the Mongo-side per-requester ACL.</p>
 */
@Tag("brownfield_debt")
@Tag("brownfield_debt_pair_unique_sec_sql_string_concat_aspect_search")
class SqlStringConcatSearchDebtTest {

    private EmbeddedDatabase db;
    private SearchRepository repo;

    @BeforeEach
    void setUp() {
        db = new EmbeddedDatabaseBuilder()
            .setType(EmbeddedDatabaseType.H2)
            .generateUniqueName(true)
            .build();
        JdbcTemplate jdbc = new JdbcTemplate(db);
        jdbc.execute("CREATE TABLE foiaRequests (id VARCHAR(64) PRIMARY KEY, status VARCHAR(32))");
        jdbc.update("INSERT INTO foiaRequests(id, status) VALUES (?, ?)", "r-1", "PROPOSED");
        jdbc.update("INSERT INTO foiaRequests(id, status) VALUES (?, ?)", "r-2", "UNDER_REVIEW");
        jdbc.update("INSERT INTO foiaRequests(id, status) VALUES (?, ?)", "r-3", "APPROVED_FOR_RELEASE");
        jdbc.update("INSERT INTO foiaRequests(id, status) VALUES (?, ?)", "r-4", "WITHHELD");
        repo = new SearchRepository(jdbc);
    }

    @Test
    void searchByStatusRejectsSqlInjection_DEBT_LOCKED() {
        int total = repo.totalCount();
        int injected = repo.searchByStatus("' OR '1'='1").size();

        // EXPECTED-AFTER-FIX: a parameterized query treats the injection
        // string as a literal status (matching 0 rows); pre-fix, the
        // concatenated SQL returns every row.
        assertThat(injected)
            .as("Pair-unique debt sec-sql-string-concat-aspect-search: "
                + "searchByStatus must use parameterized SQL. Currently the "
                + "raw concat lets `' OR '1'='1` enumerate every row in "
                + "foiaRequests — bypasses the Mongo-side per-requester ACL. "
                + "Fix lands W4 (OWASP A03 Injection).")
            .isLessThan(total);
    }
}
