package com.karsunfde.foiapipeline.redactionreview;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.web.client.RestTemplate;

/**
 * foia-response-pipeline — RedactionReview Service.
 *
 * Coordinates redactionReview panels for foiaRequests. Calls foia-request-service
 * synchronously to fetch foiaRequest data (⚠ no circuit breaker — Item 3).
 *
 * Brownfield-debt items in this service:
 *   - Item 3 — No Resilience4j circuit breaker on outbound calls
 *   - Item 6 — Logs traceId (inconsistent with X-Request-ID / correlationId)
 *   - Item 11 — Dockerfile uses :latest
 */
@SpringBootApplication
public class RedactionReviewServiceApplication {

    public static void main(String[] args) {
        SpringApplication.run(RedactionReviewServiceApplication.class, args);
    }

    /**
     * ⚠ DELIBERATE — Item 3: no timeout configuration, no error handler, no
     * circuit breaker wrapper. A slow foia-request-service will pile threads
     * on this RestTemplate.
     */
    @Bean
    public RestTemplate restTemplate() {
        return new RestTemplate();
    }
}
