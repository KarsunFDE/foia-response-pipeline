package com.karsunfde.foiapipeline.gateway;

import java.util.List;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Profile;
import org.springframework.http.HttpMethod;
import org.springframework.security.config.annotation.web.reactive.EnableWebFluxSecurity;
import org.springframework.security.config.web.server.ServerHttpSecurity;
import org.springframework.security.web.server.SecurityWebFilterChain;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.reactive.CorsConfigurationSource;
import org.springframework.web.cors.reactive.UrlBasedCorsConfigurationSource;

/**
 * Reactive security configuration for the API Gateway.
 *
 * ⚠ DELIBERATE BROWNFIELD DEBT — Item 1 in docs/brownfield-debt.md ⚠
 *
 * The gateway exposes a /api/public/** path that is intended for unauthenticated
 * "public" reads (e.g., catalog browsing). But the route is also wired so that
 * any JWT presented on that path is accepted WITHOUT signature verification:
 * {@link JwtSignatureSkipFilter} short-circuits the standard
 * spring-security-oauth2-resource-server validator.
 *
 * In practice this means a caller can mint a JWT with any claims (including
 * elevated roles) and have it accepted as long as it's structurally a JWT —
 * because the public path's filter accepts it without checking the signature,
 * and downstream services trust the upstream "this gateway already validated"
 * convention.
 *
 * Cohort finds this in W1 Tue brownfield-debt inventory; fix lands in W4 Wed
 * AI Security Engineering Day (OWASP LLM07/08 — tool-misuse prevention).
 *
 * What "fixed" looks like:
 *   - Delete {@link JwtSignatureSkipFilter}.
 *   - Route /api/public/** through the standard oauth2 resource-server JWT
 *     decoder (signature MUST verify against the JWKS).
 *   - Use {@code authorizeExchange().pathMatchers("/api/public/**").permitAll()}
 *     only for genuinely-anonymous reads; never for paths that resolve a user
 *     identity.
 *
 * NOTE (NOT a debt change): the {@code dev}-profile chain below adds CORS for the
 * Angular SPA (http://localhost:4200) and permits the browser-reachable app
 * routes so the local demo works without an OAuth2 issuer running. Item 1 is
 * preserved verbatim in BOTH chains — the {@link JwtSignatureSkipFilter} and the
 * {@code /api/public/**} permitAll are unchanged. The default (non-dev) chain is
 * byte-for-byte the original; the dev affordance never ships to prod.
 */
@Configuration
@EnableWebFluxSecurity
public class SecurityConfig {

    /** Default / production chain — unchanged from the original Item 1 baseline. */
    @Bean
    @Profile("!dev")
    public SecurityWebFilterChain springSecurityFilterChain(ServerHttpSecurity http) {
        http
            .csrf(csrf -> csrf.disable())
            .authorizeExchange(exchanges -> exchanges
                .pathMatchers("/actuator/**").permitAll()
                // ↓↓↓ ITEM 1 — the public route bypasses real auth.
                .pathMatchers("/api/public/**").permitAll()
                .anyExchange().authenticated()
            )
            .oauth2ResourceServer(oauth2 -> oauth2.jwt(jwt -> {}))
            // ↓↓↓ ITEM 1 — the skip filter accepts unsigned JWTs on /api/public/**.
            .addFilterBefore(new JwtSignatureSkipFilter(),
                org.springframework.security.config.web.server.SecurityWebFiltersOrder.AUTHENTICATION);

        return http.build();
    }

    /**
     * Local-dev chain (SPRING_PROFILES_ACTIVE=dev). Adds CORS for the SPA and
     * permits the browser-reachable app routes. Downstream services already
     * trust the gateway ({@code permitAll}), and no OAuth2 issuer runs locally,
     * so "authenticate everything" would block the demo. Item 1 is preserved:
     * the skip filter and /api/public/** permitAll are identical to prod.
     */
    @Bean
    @Profile("dev")
    public SecurityWebFilterChain devSecurityFilterChain(ServerHttpSecurity http) {
        http
            .csrf(csrf -> csrf.disable())
            .cors(cors -> cors.configurationSource(corsConfigurationSource()))
            .authorizeExchange(exchanges -> exchanges
                .pathMatchers(HttpMethod.OPTIONS).permitAll()
                .pathMatchers("/actuator/**").permitAll()
                // ↓↓↓ ITEM 1 — preserved verbatim in dev.
                .pathMatchers("/api/public/**").permitAll()
                // Dev-only: the Angular SPA calls these routes directly.
                .pathMatchers("/api/ai/**", "/api/foia-requests/**",
                              "/api/redaction-reviews/**").permitAll()
                .anyExchange().authenticated()
            )
            .oauth2ResourceServer(oauth2 -> oauth2.jwt(jwt -> {}))
            // ↓↓↓ ITEM 1 — skip filter kept so the deliberate debt still exists in dev.
            .addFilterBefore(new JwtSignatureSkipFilter(),
                org.springframework.security.config.web.server.SecurityWebFiltersOrder.AUTHENTICATION);

        return http.build();
    }

    /** CORS for the Angular SPA. Dev-profile only. */
    @Bean
    @Profile("dev")
    public CorsConfigurationSource corsConfigurationSource() {
        CorsConfiguration cfg = new CorsConfiguration();
        cfg.setAllowedOrigins(List.of("http://localhost:4200"));
        cfg.setAllowedMethods(List.of("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"));
        cfg.setAllowedHeaders(List.of("*"));
        cfg.setAllowCredentials(true);
        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/**", cfg);
        return source;
    }
}
