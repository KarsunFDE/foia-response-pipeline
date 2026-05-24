package com.karsunfde.foiapipeline.foia_request;

import com.karsunfde.foiapipeline.foia_request.audit.AuditLogger;
import com.karsunfde.foiapipeline.foia_request.dto.FoiaRequestCreateRequest;
import com.karsunfde.foiapipeline.foia_request.model.FoiaRequest;
import com.karsunfde.foiapipeline.foia_request.repository.FoiaRequestRepository;
import com.karsunfde.foiapipeline.foia_request.service.FoiaRequestService;
import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * Locked-failing tests for brownfield-debt item 9
 * (no-owasp-input-sanitization in foia-request-service).
 *
 * Convention (see fde-10-week/pipeline/T27-debt-enforcement-spec.md):
 *   Tests assert the post-modernization invariant. While the debt is present,
 *   they FAIL. After W4-Wed AI Security Day modernization (Jsoup.clean
 *   allow-list on description write paths), they PASS — at which point
 *   docs/debt-lockfile.yml must be flipped locked: true -> false with the
 *   debt-touch-approved label.
 *
 * NB: pom.xml deliberately omits spring-boot-starter-validation, so these
 * tests cannot rely on @SafeHtml. They exercise FoiaRequestService.create()
 * / .update() directly with a mocked repository, capture the saved
 * FoiaRequest, and assert that <script> markers do not survive into the
 * persisted entity.
 */
@Tag("brownfield_debt")
@Tag("brownfield_debt_9")
class InputSanitizationDebtTest {

    private static final String XSS_PAYLOAD =
        "<script>alert('xss')</script>hello world";

    @Test
    void description_sanitized_on_create_DEBT_LOCKED() {
        FoiaRequestRepository repo = mock(FoiaRequestRepository.class);
        AuditLogger audit = mock(AuditLogger.class);
        when(repo.save(any(FoiaRequest.class)))
            .thenAnswer(inv -> inv.getArgument(0));
        FoiaRequestService svc = new FoiaRequestService(repo, audit);

        FoiaRequestCreateRequest req = new FoiaRequestCreateRequest();
        req.setAgencyId("agency-a");
        req.setTitle("Procurement of widgets");
        req.setDescription(XSS_PAYLOAD);
        req.setStatus("DRAFT");

        svc.create(req, "user@example.com");

        ArgumentCaptor<FoiaRequest> captor =
            ArgumentCaptor.forClass(FoiaRequest.class);
        verify(repo).save(captor.capture());
        String stored = captor.getValue().getDescription();

        // EXPECTED-AFTER-FIX: Jsoup.clean strips <script> tags on write.
        // While debt locked: stored == XSS_PAYLOAD verbatim -> these fail.
        assertThat(stored)
            .as("create() must sanitize <script> tags from description")
            .doesNotContain("<script>")
            .doesNotContain("</script>");
    }

    @Test
    void description_sanitized_on_update_DEBT_LOCKED() {
        FoiaRequestRepository repo = mock(FoiaRequestRepository.class);
        AuditLogger audit = mock(AuditLogger.class);

        FoiaRequest existing = new FoiaRequest();
        existing.setId("sol-1");
        existing.setAgencyId("agency-a");
        existing.setTitle("original title");
        existing.setDescription("clean original");
        existing.setStatus("DRAFT");

        when(repo.findById(anyString())).thenReturn(Optional.of(existing));
        when(repo.save(any(FoiaRequest.class)))
            .thenAnswer(inv -> inv.getArgument(0));
        FoiaRequestService svc = new FoiaRequestService(repo, audit);

        FoiaRequestCreateRequest req = new FoiaRequestCreateRequest();
        req.setAgencyId("agency-a");
        req.setTitle("updated title");
        req.setDescription(XSS_PAYLOAD);
        req.setStatus("DRAFT");

        svc.update("sol-1", req, "user@example.com");

        ArgumentCaptor<FoiaRequest> captor =
            ArgumentCaptor.forClass(FoiaRequest.class);
        verify(repo).save(captor.capture());
        String stored = captor.getValue().getDescription();

        // EXPECTED-AFTER-FIX: update() also sanitizes. Locked: passthrough.
        assertThat(stored)
            .as("update() must sanitize <script> tags from description")
            .doesNotContain("<script>")
            .doesNotContain("</script>");
    }
}
