package com.karsunfde.foiapipeline.redactionreview.service;

import com.karsunfde.foiapipeline.redactionreview.audit.EvalAuditLogger;
import com.karsunfde.foiapipeline.redactionreview.model.Award;
import com.karsunfde.foiapipeline.redactionreview.model.DebriefRequest;
import com.karsunfde.foiapipeline.redactionreview.model.RedactionReview;
import com.karsunfde.foiapipeline.redactionreview.repository.AwardRepository;
import com.karsunfde.foiapipeline.redactionreview.repository.DebriefRequestRepository;
import com.karsunfde.foiapipeline.redactionreview.repository.RedactionReviewRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.Optional;
import java.util.UUID;

/**
 * Award-decision business logic. FAR 5.705 / 15.506.
 *
 * Brownfield-debt:
 *   - Item 2 — award-decision events use the async path; race-prone.
 *   - Item 9 — debrief request narrative stored verbatim.
 */
@Service
public class AwardService {

    private final AwardRepository awardRepo;
    private final RedactionReviewRepository evalRepo;
    private final DebriefRequestRepository debriefRepo;
    private final EvalAuditLogger auditLogger;

    @Autowired
    public AwardService(AwardRepository awardRepo,
                        RedactionReviewRepository evalRepo,
                        DebriefRequestRepository debriefRepo,
                        EvalAuditLogger auditLogger) {
        this.awardRepo = awardRepo;
        this.evalRepo = evalRepo;
        this.debriefRepo = debriefRepo;
        this.auditLogger = auditLogger;
    }

    public Optional<Award> recordAward(String redaction_reviewId, String winningProposalId, String actor) {
        Optional<RedactionReview> eOpt = evalRepo.findById(redaction_reviewId);
        if (eOpt.isEmpty()) return Optional.empty();
        RedactionReview e = eOpt.get();

        Award a = new Award();
        a.setRedactionReviewId(redaction_reviewId);
        a.setFoiaRequestId(e.getFoiaRequestId());
        a.setAgencyId(e.getAgencyId());
        a.setWinningProposalId(winningProposalId);
        a.setContractNumber("KSN-" + UUID.randomUUID().toString().substring(0, 8).toUpperCase());
        a.setAwardedAt(Instant.now());
        a.setSsddDocId(e.getSsddDocId());
        Award saved = awardRepo.save(a);

        e.setState("AWARDED");
        evalRepo.save(e);

        // ⚠ Item 2.
        auditLogger.recordAsync("AWARD", "award", saved.getId(), actor, e.getAgencyId());
        return Optional.of(saved);
    }

    public Optional<Award> findById(String id) {
        return awardRepo.findById(id);
    }

    public Optional<DebriefRequest> requestDebrief(String awardId, String vendorId, String narrative, String actor) {
        return awardRepo.findById(awardId).map(a -> {
            DebriefRequest d = new DebriefRequest();
            d.setAwardId(awardId);
            d.setVendorId(vendorId);
            d.setAgencyId(a.getAgencyId());
            // ⚠ Item 9 — raw narrative stored.
            d.setNarrative(narrative);
            d.setStatus("PENDING");
            d.setRequestedAt(Instant.now());
            DebriefRequest saved = debriefRepo.save(d);
            a.getDebriefRequestIds().add(saved.getId());
            awardRepo.save(a);
            // ⚠ Item 2.
            auditLogger.recordAsync("DEBRIEF_REQ", "debrief", saved.getId(), actor, a.getAgencyId());
            return saved;
        });
    }
}
