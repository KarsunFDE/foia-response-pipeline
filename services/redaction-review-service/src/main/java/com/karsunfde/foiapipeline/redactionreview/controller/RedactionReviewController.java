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
 *   duplicate redaction_reviews.
 */
@RestController
@RequestMapping("/api/redaction-reviews")
public class RedactionReviewController {

    private final FoiaRequestClient foia_requestClient;
    private final RedactionReviewService svc;

    @Autowired
    public RedactionReviewController(FoiaRequestClient foia_requestClient, RedactionReviewService svc) {
        this.foia_requestClient = foia_requestClient;
        this.svc = svc;
    }

    /** Fetch the foia_request snapshot the redaction_review panel is reviewing. */
    @GetMapping("/{redaction_reviewId}/foia_request/{foia_requestId}")
    public ResponseEntity<Map<String, Object>> getFoiaRequestForRedactionReview(
            @PathVariable String redaction_reviewId,
            @PathVariable String foia_requestId) {
        // ⚠ Item 3 — no circuit breaker on this hop.
        Map<String, Object> sol = foia_requestClient.getFoiaRequest(foia_requestId);
        return ResponseEntity.ok(sol);
    }

    /** Create a new redaction_review panel. ⚠ Item 3 — no idempotency key. */
    @PostMapping
    public ResponseEntity<RedactionReview> create(@RequestBody Map<String, Object> req,
                                              @RequestHeader(value = "X-User", defaultValue = "anonymous") String actor) {
        String foia_requestId = String.valueOf(req.get("foia_requestId"));
        String agencyId = (String) req.getOrDefault("agencyId", "GSA-FAS");
        return ResponseEntity.ok(svc.create(foia_requestId, agencyId, actor));
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
