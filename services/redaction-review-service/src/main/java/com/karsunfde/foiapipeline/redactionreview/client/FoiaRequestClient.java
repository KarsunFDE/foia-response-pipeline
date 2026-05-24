package com.karsunfde.foiapipeline.redaction_review.client;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

import java.util.Map;

/**
 * ⚠ DELIBERATE BROWNFIELD DEBT — Item 3 ⚠
 *
 * Calls foia-request-service over synchronous REST. No:
 *   - {@code @CircuitBreaker} (Resilience4j not on the classpath)
 *   - {@code @TimeLimiter}
 *   - {@code @Retry}
 *   - fallback method
 *   - timeout on the RestTemplate
 *   - idempotency key on state-mutating calls
 *
 * A slow upstream piles threads on this service's Tomcat connector. A load
 * test from redaction-review-service → foia-request-service (artificially slow)
 * will reproduce thread exhaustion.
 *
 * Cohort fixes in W4 Thu reliability engineering.
 */
@Component
public class FoiaRequestClient {

    private static final Logger log = LoggerFactory.getLogger(FoiaRequestClient.class);

    private final RestTemplate restTemplate;

    @Value("${foia_request.service.url:http://foia-request-service:8081}")
    private String foia_requestServiceUrl;

    @Autowired
    public FoiaRequestClient(RestTemplate restTemplate) {
        this.restTemplate = restTemplate;
    }

    /**
     * Fetch a foia_request by id from the upstream service.
     *
     * ⚠ No try/catch — a 5xx from upstream propagates as a 500 from us.
     * ⚠ No timeout — a 30-second hang upstream is a 30-second hang here.
     */
    @SuppressWarnings("unchecked")
    public Map<String, Object> getFoiaRequest(String id) {
        String url = foia_requestServiceUrl + "/api/foia-requests/" + id;
        // Item 6 — redaction-review-service uses traceId key.
        log.info("calling foia-request-service url={} traceId=N/A", url);
        return restTemplate.getForObject(url, Map.class);
    }
}
