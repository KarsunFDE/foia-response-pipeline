package com.karsunfde.foiapipeline.redactionreview.client;

import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.web.client.HttpServerErrorException;
import org.springframework.web.client.RestTemplate;

import java.lang.reflect.Field;
import java.time.Duration;
import java.time.Instant;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

/**
 * Locked-failing test for pair-unique debt item rel-retry-without-backoff
 * (D-059, Cohort #1 Pair 3 — foia-response-pipeline).
 *
 * <p>Convention: assertion = what-true-after-modernization.</p>
 *
 * <p>While debt is locked (current state): {@link AiOrchestratorClient#draft(String)}
 * retries 5× in a tight loop on 503. Total elapsed time is dominated by the
 * RestTemplate call itself — well under 2s with a mock. Detection asserts
 * "elapsed &gt; 2s" — fails because there's no backoff.</p>
 *
 * <p>After W5 fix:</p>
 * <ul>
 *   <li>Resilience4j Retry with exponentialBackoff(500ms, 2.0, 5) wraps the call</li>
 *   <li>Total elapsed after 5 failures &gt; 500 + 1000 + 2000 + 4000 = 7.5s</li>
 *   <li>Test PASSES (elapsed &gt; 2s).</li>
 * </ul>
 *
 * <p>FOIA-domain rationale: redaction-proposer batches fan out hundreds of
 * concurrent reviews when an agency uploads a multi-thousand-page responsive-
 * document set; tight-loop retries against a throttled Bedrock take the AI
 * service down for everyone.</p>
 */
@Tag("brownfield_debt")
@Tag("brownfield_debt_pair_unique_rel_retry_without_backoff")
class RetryWithoutBackoffDebtTest {

    @Test
    void aiClientUsesExponentialBackoff_DEBT_LOCKED() throws Exception {
        RestTemplate restTemplate = mock(RestTemplate.class);
        when(restTemplate.postForObject(anyString(), any(), eq(Map.class)))
            .thenThrow(new HttpServerErrorException(HttpStatus.SERVICE_UNAVAILABLE));

        AiOrchestratorClient client = new AiOrchestratorClient(restTemplate);
        // Inject aiUrl since we're not running Spring.
        Field aiUrlField = AiOrchestratorClient.class.getDeclaredField("aiUrl");
        aiUrlField.setAccessible(true);
        aiUrlField.set(client, "http://stub");

        Instant start = Instant.now();
        assertThatThrownBy(() -> client.draft("redact this responsive page"))
            .isInstanceOf(RuntimeException.class);
        Duration elapsed = Duration.between(start, Instant.now());

        // EXPECTED-AFTER-FIX: exponential backoff (500ms, 1s, 2s, 4s, …)
        // makes 5 retries take > 2 seconds total. Pre-fix: tight loop
        // completes in milliseconds.
        assertThat(elapsed)
            .as("Pair-unique debt rel-retry-without-backoff: AiOrchestratorClient.draft "
                + "must use exponential backoff (Resilience4j @Retry with "
                + "IntervalFunction.ofExponentialBackoff). Currently 5× retry "
                + "in a tight loop = thundering-herd against ai-orchestrator. "
                + "Fix lands W5 (AIOps Resilience4j anchor).")
            .isGreaterThan(Duration.ofSeconds(2));
    }
}
