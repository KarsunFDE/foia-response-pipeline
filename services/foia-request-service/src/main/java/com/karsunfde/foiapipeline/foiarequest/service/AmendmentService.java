package com.karsunfde.foiapipeline.foia_request.service;

import com.karsunfde.foiapipeline.foia_request.audit.AuditLogger;
import com.karsunfde.foiapipeline.foia_request.dto.AmendmentRequest;
import com.karsunfde.foiapipeline.foia_request.model.Amendment;
import com.karsunfde.foiapipeline.foia_request.model.FoiaRequest;
import com.karsunfde.foiapipeline.foia_request.repository.AmendmentRepository;
import com.karsunfde.foiapipeline.foia_request.repository.FoiaRequestRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.List;
import java.util.Optional;

/**
 * Amendment issuance (FAR 15.206). Workflow 2.
 *
 * Brownfield-debt items present here:
 *   - Item 2 — amendment publication writes are audit-logged via recordAsync.
 *   - Item 9 — changeSummary stored verbatim.
 *   - Item 10 — list endpoints call findByFoiaRequestId without re-checking
 *     the caller's agency claim against the foia_request's agency.
 */
@Service
public class AmendmentService {

    private static final Logger log = LoggerFactory.getLogger(AmendmentService.class);

    private final AmendmentRepository repo;
    private final FoiaRequestRepository solRepo;
    private final AuditLogger auditLogger;

    @Autowired
    public AmendmentService(AmendmentRepository repo,
                            FoiaRequestRepository solRepo,
                            AuditLogger auditLogger) {
        this.repo = repo;
        this.solRepo = solRepo;
        this.auditLogger = auditLogger;
    }

    public Optional<Amendment> issue(String foia_requestId, AmendmentRequest req, String actor) {
        Optional<FoiaRequest> solOpt = solRepo.findById(foia_requestId);
        if (solOpt.isEmpty()) return Optional.empty();
        FoiaRequest sol = solOpt.get();

        List<Amendment> existing = repo.findByFoiaRequestIdOrderByNumberAsc(foia_requestId);
        int nextNumber = existing.isEmpty() ? 1 : existing.get(existing.size() - 1).getNumber() + 1;

        Amendment a = new Amendment();
        a.setFoiaRequestId(foia_requestId);
        a.setAgencyId(sol.getAgencyId());
        a.setNumber(nextNumber);
        // ⚠ Item 9 — raw HTML stored.
        a.setChangeSummary(req.getChangeSummary());
        a.setRequiresAcknowledgement(req.isRequiresAcknowledgement());
        a.setEffectiveAt(req.getEffectiveAt() != null ? Instant.parse(req.getEffectiveAt()) : Instant.now());
        a.setCreatedAt(Instant.now());
        Amendment saved = repo.save(a);

        // ⚠ Item 2 — fire-and-forget.
        auditLogger.recordAsync("AMEND", "amendment", saved.getId(), actor, sol.getAgencyId());

        log.info("amendment issued foia_requestId={} number={} agencyId={}",
            foia_requestId, nextNumber, sol.getAgencyId());

        return Optional.of(saved);
    }

    public List<Amendment> listForFoiaRequest(String foia_requestId) {
        // ⚠ Item 10 — does not re-check caller's agency claim.
        return repo.findByFoiaRequestIdOrderByNumberAsc(foia_requestId);
    }
}
