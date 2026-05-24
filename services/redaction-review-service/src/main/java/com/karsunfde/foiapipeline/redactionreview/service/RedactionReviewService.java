package com.karsunfde.foiapipeline.redactionreview.service;

import com.karsunfde.foiapipeline.redactionreview.audit.EvalAuditLogger;
import com.karsunfde.foiapipeline.redactionreview.client.AiOrchestratorClient;
import com.karsunfde.foiapipeline.redactionreview.client.FoiaRequestClient;
import com.karsunfde.foiapipeline.redactionreview.model.RedactionReview;
import com.karsunfde.foiapipeline.redactionreview.model.RedactionReviewScore;
import com.karsunfde.foiapipeline.redactionreview.repository.RedactionReviewRepository;
import com.karsunfde.foiapipeline.redactionreview.repository.RedactionReviewScoreRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.*;
import java.util.stream.Collectors;

/**
 * Workflow 4 — redactionReview → consensus → source selection → award (pre-award).
 *
 * Brownfield-debt items reinforced:
 *   - Item 3 — calls foia-request-service for each proposal text via
 *     FoiaRequestClient (no circuit breaker).
 *   - Item 2 — state transitions audit-logged via async.
 *   - Item 4 reinforcement — SSDD draft response from ai-orchestrator goes
 *     straight back; no structured-output schema enforcement.
 */
@Service
public class RedactionReviewService {

    private static final Logger log = LoggerFactory.getLogger(RedactionReviewService.class);

    private final RedactionReviewRepository evalRepo;
    private final RedactionReviewScoreRepository scoreRepo;
    private final FoiaRequestClient foiaRequestClient;
    private final AiOrchestratorClient aiClient;
    private final EvalAuditLogger auditLogger;

    @Autowired
    public RedactionReviewService(RedactionReviewRepository evalRepo,
                             RedactionReviewScoreRepository scoreRepo,
                             FoiaRequestClient foiaRequestClient,
                             AiOrchestratorClient aiClient,
                             EvalAuditLogger auditLogger) {
        this.evalRepo = evalRepo;
        this.scoreRepo = scoreRepo;
        this.foiaRequestClient = foiaRequestClient;
        this.aiClient = aiClient;
        this.auditLogger = auditLogger;
    }

    public RedactionReview create(String foiaRequestId, String agencyId, String actor) {
        RedactionReview e = new RedactionReview();
        e.setFoiaRequestId(foiaRequestId);
        e.setAgencyId(agencyId);
        e.setState("OPEN");
        e.setCreatedAt(Instant.now());
        RedactionReview saved = evalRepo.save(e);
        auditLogger.recordAsync("EVAL_CREATE", "redactionReview", saved.getId(), actor, agencyId);
        return saved;
    }

    public Optional<RedactionReview> findById(String id) {
        return evalRepo.findById(id);
    }

    public Optional<RedactionReview> assignPanel(String redactionReviewId, List<String> panelMembers, String actor) {
        return evalRepo.findById(redactionReviewId).map(e -> {
            e.setPanelMembers(panelMembers);
            e.setState("PANEL_ASSIGNED");
            RedactionReview saved = evalRepo.save(e);
            auditLogger.recordAsync("EVAL_PANEL_ASSIGN", "redactionReview", saved.getId(),
                actor, e.getAgencyId());
            return saved;
        });
    }

    public Optional<RedactionReviewScore> submitScore(String redactionReviewId, RedactionReviewScore in, String actor) {
        Optional<RedactionReview> eOpt = evalRepo.findById(redactionReviewId);
        if (eOpt.isEmpty()) return Optional.empty();
        RedactionReview e = eOpt.get();

        // ⚠ Item 3 — fetches proposal context from foia-request-service for
        // each score submission. No circuit breaker; under TEP-week load
        // this is the thread-exhaustion reproducer.
        Map<String, Object> proposal = foiaRequestClient.getFoiaRequest(in.getProposalId());
        log.info("score submission redactionReviewId={} proposalId={} proposal-loaded={}",
            redactionReviewId, in.getProposalId(), proposal != null);

        in.setRedactionReviewId(redactionReviewId);
        in.setScoredAt(Instant.now());
        RedactionReviewScore saved = scoreRepo.save(in);

        // ⚠ Item 2.
        auditLogger.recordAsync("EVAL_SCORE", "score", saved.getId(),
            actor, e.getAgencyId());

        // Promote redactionReview state on first score.
        if (!"SCORING".equals(e.getState())) {
            e.setState("SCORING");
            evalRepo.save(e);
        }
        return Optional.of(saved);
    }

    /** Aggregate panel consensus per proposal × factor. */
    public Map<String, Map<String, Double>> consensus(String redactionReviewId) {
        List<RedactionReviewScore> scores = scoreRepo.findByRedactionReviewId(redactionReviewId);
        Map<String, List<RedactionReviewScore>> byProposal = scores.stream()
            .collect(Collectors.groupingBy(RedactionReviewScore::getProposalId));
        Map<String, Map<String, Double>> out = new LinkedHashMap<>();
        for (Map.Entry<String, List<RedactionReviewScore>> p : byProposal.entrySet()) {
            Map<String, Double> byFactor = p.getValue().stream()
                .collect(Collectors.groupingBy(
                    RedactionReviewScore::getFactorId,
                    Collectors.averagingInt(RedactionReviewScore::getScore)));
            out.put(p.getKey(), byFactor);
        }
        return out;
    }

    /** Generate Source Selection Decision Document via ai-orchestrator. */
    public Optional<Map<String, Object>> draftSsdd(String redactionReviewId, String actor) {
        return evalRepo.findById(redactionReviewId).map(e -> {
            // ⚠ Item 4 reinforcement — raw response returned; no schema check.
            Map<String, Object> resp = aiClient.draftSsdd(redactionReviewId);
            e.setState("CONSENSUS");
            e.setConsensusAt(Instant.now());
            // Store doc id placeholder from response if present.
            if (resp != null && resp.get("clause_id") != null) {
                e.setSsddDocId(resp.get("clause_id").toString());
            }
            evalRepo.save(e);
            auditLogger.recordAsync("SSDD_DRAFT", "redactionReview", redactionReviewId,
                actor, e.getAgencyId());
            return resp;
        });
    }
}
