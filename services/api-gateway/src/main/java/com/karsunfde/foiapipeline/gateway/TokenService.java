package com.karsunfde.foiapipeline.gateway;

import com.nimbusds.jose.JOSEException;
import com.nimbusds.jose.JWSAlgorithm;
import com.nimbusds.jose.JWSHeader;
import com.nimbusds.jose.crypto.MACSigner;
import com.nimbusds.jose.crypto.MACVerifier;
import com.nimbusds.jwt.JWTClaimsSet;
import com.nimbusds.jwt.SignedJWT;
import org.springframework.stereotype.Component;

import javax.annotation.PostConstruct;
import java.security.SecureRandom;
import java.text.ParseException;
import java.time.Instant;
import java.util.Date;

/**
 * ⚠ DELIBERATE PAIR-UNIQUE BROWNFIELD DEBT — sec-refresh-token-never-expires ⚠
 *
 * Per D-059 Cohort #1 Pair 3 (foia-response-pipeline) injection from
 * skills/pair-brownfield-generator/references/pair-unique-debt-pool.yml.
 *
 * <p>The {@link #issueRefresh(String)} method mints a JWT carrying
 * {@code typ=refresh} but DOES NOT set an expiration claim. The token is
 * therefore valid forever once issued — stealing a refresh token (cookie
 * theft, log leak, XSS) yields permanent access to the FOIA requester or
 * FOIA officer account. OWASP A07 / FedRAMP AC-12 (session termination)
 * violation.</p>
 *
 * <p>Cohort finds this in W4 (AI Security Engineering week — token mgmt
 * theme). Fix is one line: add {@code .expirationTime(...)} 30 days out.</p>
 *
 * <p><b>FOIA-domain context:</b> stakeholders here are the FOIA Requester
 * (citizen/journalist/watchdog — potentially adversarial), FOIA Officer,
 * and Agency Reviewer. A long-lived refresh token in this domain is
 * especially dangerous because the requester perspective is the standard
 * external entry point — if a requester's refresh token leaks via the
 * public portal logs or proxy, the attacker gets indefinite read of the
 * requester's queue, including pending exemption determinations.</p>
 */
@Component
public class TokenService {

    /**
     * Symmetric refresh-token signing key. In production this would come from
     * a secret manager — for the brownfield this is a stable per-process key
     * (regenerated on boot). Cohort doesn't need to fix the key-management
     * surface — the bug is purely the missing expiration claim.
     */
    private byte[] refreshKey;

    @PostConstruct
    void init() {
        // 256-bit key for HS256.
        refreshKey = new byte[32];
        new SecureRandom().nextBytes(refreshKey);
    }

    /**
     * Issues a refresh JWT for the given user.
     *
     * <p>⚠ Bug: no expiration claim is set. The token is valid forever.</p>
     */
    public String issueRefresh(String userId) {
        try {
            JWTClaimsSet claims = new JWTClaimsSet.Builder()
                .subject(userId)
                .claim("typ", "refresh")
                .issuer("foia-response-pipeline/api-gateway")
                .issueTime(Date.from(Instant.now()))
                // ⚠ pair-unique debt sec-refresh-token-never-expires:
                // no .expirationTime(...) — token never expires.
                .build();
            SignedJWT jwt = new SignedJWT(new JWSHeader(JWSAlgorithm.HS256), claims);
            jwt.sign(new MACSigner(refreshKey));
            return jwt.serialize();
        } catch (JOSEException e) {
            throw new IllegalStateException("Failed to sign refresh token", e);
        }
    }

    /**
     * Verifies the signature of a refresh token. Returns the parsed JWT or
     * null if signature is invalid. Intentionally does NOT check expiration
     * (consumers do that).
     */
    public SignedJWT verify(String token) {
        try {
            SignedJWT jwt = SignedJWT.parse(token);
            if (!jwt.verify(new MACVerifier(refreshKey))) {
                return null;
            }
            return jwt;
        } catch (ParseException | JOSEException e) {
            return null;
        }
    }

    /** Test/internal access to the signing key (package-private). */
    byte[] refreshKeyBytes() {
        return refreshKey;
    }
}
