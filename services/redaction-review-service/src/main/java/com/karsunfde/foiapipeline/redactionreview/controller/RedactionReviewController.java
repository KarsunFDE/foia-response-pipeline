package com.karsunfde.foiapipeline.redactionreview.controller;

import com.karsunfde.foiapipeline.redactionreview.client.FoiaRequestClient;
import com.karsunfde.foiapipeline.redactionreview.model.RedactionReview;
import com.karsunfde.foiapipeline.redactionreview.model.RedactionReviewScore;
import com.karsunfde.foiapipeline.redactionreview.service.RedactionReviewService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/**
 * RedactionReview panel REST surface — Workflow 4 (eval → consensus → SSDD).
 *
 * Endpoints (feature-inventory-target.md, redaction-review-service rows):
 *   POST   /api/redaction-reviews
 *   GET    /api/redaction-reviews/{id}
 *   POST   /api/redaction-reviews/{id}/panel
 *   POST   /api/redaction-reviews/{id}/scores
 *   GET    /api/redaction-reviews/{id}/consensus
 *   POST   /api/redaction-reviews/{id}/ssdd
 *
 * ⚠ DELIBERATE — Item 3 reinforcement:
 *   POST /api/redaction-reviews is a state-mutating endpoint that does NOT accept
 *   or honour an Idempotency-Key header. A retry from the client creates
 *   duplicate redactionReviews.
 */
@RestController
@RequestMapping("/api/redaction-reviews")
public class RedactionReviewController {

    private final FoiaRequestClient foiaRequestClient;
    private final RedactionReviewService svc;

    @Autowired
    public RedactionReviewController(FoiaRequestClient foiaRequestClient, RedactionReviewService svc) {
        this.foiaRequestClient = foiaRequestClient;
        this.svc = svc;
    }

    /** Fetch the foiaRequest snapshot the redactionReview panel is reviewing. */
    @GetMapping("/{redactionReviewId}/foiaRequest/{foiaRequestId}")
    public ResponseEntity<Map<String, Object>> getFoiaRequestForRedactionReview(
            @PathVariable String redactionReviewId,
            @PathVariable String foiaRequestId) {
        // ⚠ Item 3 — no circuit breaker on this hop.
        Map<String, Object> sol = foiaRequestClient.getFoiaRequest(foiaRequestId);
        return ResponseEntity.ok(sol);
    }

    /** Create a new redactionReview panel. ⚠ Item 3 — no idempotency key. */
    @PostMapping
    public ResponseEntity<RedactionReview> create(@RequestBody Map<String, Object> req,
                                              @RequestHeader(value = "X-User", defaultValue = "anonymous") String actor) {
        String foiaRequestId = String.valueOf(req.get("foiaRequestId"));
        String agencyId = (String) req.getOrDefault("agencyId", "GSA-FAS");
        return ResponseEntity.ok(svc.create(foiaRequestId, agencyId, actor));
    }

    @GetMapping("/{id}")
    public ResponseEntity<RedactionReview> get(@PathVariable String id) {
        return svc.findById(id)
            .map(ResponseEntity::ok)
            .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping("/{id}/panel")
    public ResponseEntity<RedactionReview> assignPanel(
            @PathVariable String id,
            @RequestBody Map<String, List<String>> body,
            @RequestHeader(value = "X-User", defaultValue = "anonymous") String actor) {
        return svc.assignPanel(id, body.getOrDefault("panelMembers", List.of()), actor)
            .map(ResponseEntity::ok)
            .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping("/{id}/scores")
    public ResponseEntity<RedactionReviewScore> submitScore(
            @PathVariable String id,
            @RequestBody RedactionReviewScore score,
            @RequestHeader(value = "X-User", defaultValue = "anonymous") String actor) {
        return svc.submitScore(id, score, actor)
            .map(ResponseEntity::ok)
            .orElse(ResponseEntity.notFound().build());
    }

    @GetMapping("/{id}/consensus")
    public Map<String, Map<String, Double>> consensus(@PathVariable String id) {
        return svc.consensus(id);
    }

    @PostMapping("/{id}/ssdd")
    public ResponseEntity<Map<String, Object>> ssdd(
            @PathVariable String id,
            @RequestHeader(value = "X-User", defaultValue = "anonymous") String actor) {
        return svc.draftSsdd(id, actor)
            .map(ResponseEntity::ok)
            .orElse(ResponseEntity.notFound().build());
    }
}
