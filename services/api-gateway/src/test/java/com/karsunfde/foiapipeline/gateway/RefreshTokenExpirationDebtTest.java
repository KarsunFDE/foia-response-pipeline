package com.karsunfde.foiapipeline.gateway;

import com.nimbusds.jwt.SignedJWT;
import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;

import java.time.Duration;
import java.time.Instant;
import java.util.Date;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Locked-failing test for pair-unique debt item sec-refresh-token-never-expires
 * (D-059, Cohort #1 Pair 3 — foia-response-pipeline).
 *
 * <p>Convention: assertion = what-true-after-modernization.</p>
 *
 * <p>While debt is locked (current state): {@link TokenService#issueRefresh(String)}
 * mints a JWT with no {@code exp} claim. The token is valid forever.</p>
 *
 * <p>After W4 fix:</p>
 * <ul>
 *   <li>Builder includes {@code .expirationTime(Date.from(Instant.now().plus(30, DAYS)))}</li>
 *   <li>Returned JWT has a parseable {@code exp} claim within ~30 days of issue</li>
 *   <li>Test PASSES.</li>
 * </ul>
 *
 * <p>FOIA-domain rationale: a refresh token issued to a FOIA requester (citizen,
 * journalist) on the public portal is a primary attack-surface artifact. Indefinite
 * lifetime = indefinite read on the requester's pending FoiaRequest queue and any
 * proposed ExemptionDetermination / ResponsivePages.</p>
 */
@Tag("brownfield_debt")
@Tag("brownfield_debt_pair_unique_sec_refresh_token_never_expires")
class RefreshTokenExpirationDebtTest {

    @Test
    void refreshTokenHasExpiration_DEBT_LOCKED() throws Exception {
        TokenService tokenService = new TokenService();
        // Mirror @PostConstruct so the test runs without Spring context.
        java.lang.reflect.Method init = TokenService.class.getDeclaredMethod("init");
        init.setAccessible(true);
        init.invoke(tokenService);

        String token = tokenService.issueRefresh("foia-requester-1");
        SignedJWT jwt = SignedJWT.parse(token);
        Date exp = jwt.getJWTClaimsSet().getExpirationTime();

        // EXPECTED-AFTER-FIX: refresh tokens MUST carry an expiration claim,
        // and that expiration MUST be within 31 days (30-day cap + slack).
        assertThat(exp)
            .as("Pair-unique debt sec-refresh-token-never-expires: refresh JWT "
                + "must carry an `exp` claim. Currently null → stolen refresh "
                + "tokens never invalidate. Fix lands W4 (OWASP A07, "
                + "FedRAMP AC-12).")
            .isNotNull();

        assertThat(exp)
            .as("Refresh token expiration must be within 31 days of issue")
            .isBefore(Date.from(Instant.now().plus(Duration.ofDays(31))));
    }
}
