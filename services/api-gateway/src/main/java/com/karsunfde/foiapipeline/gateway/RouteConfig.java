package com.karsunfde.foiapipeline.gateway;

import org.springframework.cloud.gateway.route.RouteLocator;
import org.springframework.cloud.gateway.route.builder.RouteLocatorBuilder;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * Gateway route definitions.
 *
 * Routes:
 *   /api/foia-requests/**   → foia-request-service:8081
 *   /api/redaction-reviews/**     → redaction-review-service:8082
 *   /api/ai/**              → ai-orchestrator:8000
 *   /api/public/**          → foia-request-service (signature-skipped path — Item 1)
 */
@Configuration
public class RouteConfig {

    @Bean
    public RouteLocator routes(RouteLocatorBuilder builder) {
        String foia_requestUrl = System.getenv().getOrDefault(
            "SOLICITATION_SERVICE_URL", "http://foia-request-service:8081");
        String redaction_reviewUrl = System.getenv().getOrDefault(
            "EVALUATION_SERVICE_URL", "http://redaction-review-service:8082");
        String aiUrl = System.getenv().getOrDefault(
            "AI_ORCHESTRATOR_URL", "http://ai-orchestrator:8000");

        return builder.routes()
            .route("foia_requests", r -> r.path("/api/foia-requests/**").uri(foia_requestUrl))
            .route("redaction_reviews",   r -> r.path("/api/redaction-reviews/**").uri(redaction_reviewUrl))
            .route("ai",            r -> r.path("/api/ai/**").uri(aiUrl))
            // Item 1 — public path forwards to foia-request-service after signature-skip.
            .route("public",        r -> r.path("/api/public/**").uri(foia_requestUrl))
            .build();
    }
}
