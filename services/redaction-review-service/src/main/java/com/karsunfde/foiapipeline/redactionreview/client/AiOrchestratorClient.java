package com.karsunfde.foiapipeline.redactionreview.client;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.client.HttpServerErrorException;
import org.springframework.web.client.RestTemplate;

import java.util.HashMap;
import java.util.Map;

/**
 * Calls ai-orchestrator for SSDD draft + factor-suggest narrative.
 *
 * ⚠ Item 3 reinforcement — same RestTemplate, no circuit breaker.
 * ⚠ Item 6 — no correlation-id forwarded.
 *
 * ⚠ DELIBERATE PAIR-UNIQUE BROWNFIELD DEBT — rel-retry-without-backoff ⚠
 * Per D-059 Cohort #1 Pair 3 (foia-response-pipeline). The new {@link #draft(String)}
 * entry-point retries up to 5 times with NO backoff (thundering-herd antipattern).
 * Cohort fixes in W5 (AIOps Resilience4j anchor). See
 * services/foia-response-pipeline/docs/pair-unique-debt.md.
 */
@Component
public class AiOrchestratorClient {

    private static final Logger log = LoggerFactory.getLogger(AiOrchestratorClient.class);

    private final RestTemplate restTemplate;

    @Value("${ai.orchestrator.url:http://ai-orchestrator:8000}")
    private String aiUrl;

    @Autowired
    public AiOrchestratorClient(RestTemplate restTemplate) {
        this.restTemplate = restTemplate;
    }

    @SuppressWarnings("unchecked")
    public Map<String, Object> draftSsdd(String redactionReviewId) {
        Map<String, Object> body = new HashMap<>();
        body.put("topic", "SSDD for redactionReview " + redactionReviewId);
        body.put("constraints", "FAR 15.308 tradeoff narrative");
        log.info("calling ai-orchestrator /eval/ssdd-draft redactionReviewId={} traceId=N/A", redactionReviewId);
        return restTemplate.postForObject(aiUrl + "/eval/ssdd-draft", body, Map.class);
    }

    @SuppressWarnings("unchecked")
    public Map<String, Object> factorSuggest(String proposalText, String factorId) {
        Map<String, Object> body = new HashMap<>();
        body.put("topic", "factor " + factorId);
        body.put("constraints", proposalText);
        return restTemplate.postForObject(aiUrl + "/eval/factor-suggest", body, Map.class);
    }

    /**
     * Calls ai-orchestrator's draft endpoint for a redaction-review narrative.
     *
     * <p>⚠ Pair-unique debt rel-retry-without-backoff: retries up to 5 times
     * with NO backoff. Under a transient 503 from ai-orchestrator (or
     * upstream Bedrock throttling), this client hammers the AI service 5
     * times in tight succession from every concurrent request — classic
     * thundering-herd. FOIA-domain twist: redaction-proposer batches can
     * fan out hundreds of in-flight reviews simultaneously when an agency
     * uploads a multi-thousand-page responsive-document set.</p>
     *
     * @param input prompt input (typically a ResponsivePages excerpt for
     *              redaction-proposal)
     * @return ai-orchestrator response body
     */
    @SuppressWarnings("unchecked")
    public Map<String, Object> draft(String input) {
        Map<String, Object> body = new HashMap<>();
        body.put("input", input);
        // ⚠ pair-unique debt rel-retry-without-backoff:
        // tight-loop retry with no backoff.
        RuntimeException last = null;
        for (int i = 0; i < 5; i++) {
            try {
                return restTemplate.postForObject(aiUrl + "/draft", body, Map.class);
            } catch (HttpServerErrorException e) {
                last = e;
                // ⚠ retry immediately, no backoff
            }
        }
        throw new RuntimeException("AI orchestrator failing", last);
    }
}
