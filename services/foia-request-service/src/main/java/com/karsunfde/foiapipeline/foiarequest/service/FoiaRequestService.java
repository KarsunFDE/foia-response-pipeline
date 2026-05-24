package com.karsunfde.foiapipeline.foia_request.service;

import com.karsunfde.foiapipeline.foia_request.audit.AuditLogger;
import com.karsunfde.foiapipeline.foia_request.dto.FoiaRequestCreateRequest;
import com.karsunfde.foiapipeline.foia_request.model.FoiaRequest;
import com.karsunfde.foiapipeline.foia_request.repository.FoiaRequestRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.List;
import java.util.Optional;

/**
 * FoiaRequest business logic. Workflow 1 (drafting -> publication).
 *
 * State machine:
 *   DRAFT -> INTERNAL_REVIEW -> READY_TO_PUBLISH -> PUBLISHED -> (AMENDED)* -> CLOSED
 *   CANCELLED reachable from any pre-PUBLISHED state.
 *
 * Brownfield-debt items present in this class:
 *   - Item 2 — {@link AuditLogger#recordAsync} runs after response flushes.
 *   - Item 9 — description is stored verbatim (no Jsoup.clean).
 *   - Item 10 — listAll calls repo.findAll() not findByAgencyId.
 */
@Service
public class FoiaRequestService {

    private static final Logger log = LoggerFactory.getLogger(FoiaRequestService.class);

    private final FoiaRequestRepository repo;
    private final AuditLogger auditLogger;

    @Autowired
    public FoiaRequestService(FoiaRequestRepository repo, AuditLogger auditLogger) {
        this.repo = repo;
        this.auditLogger = auditLogger;
    }

    public FoiaRequest create(FoiaRequestCreateRequest req, String actor) {
        FoiaRequest s = new FoiaRequest();
        s.setAgencyId(req.getAgencyId());
        s.setTitle(req.getTitle());
        // ⚠ Item 9 — no Jsoup.clean, no escape, no length cap.
        s.setDescription(req.getDescription());
        s.setStatus(req.getStatus() != null ? req.getStatus() : "DRAFT");
        s.setCreatedAt(Instant.now());
        s.setUpdatedAt(Instant.now());

        FoiaRequest saved = repo.save(s);

        // ⚠ Item 2 — fire-and-forget. Returns immediately, controller flushes
        //   response, audit may or may not land.
        auditLogger.recordAsync("CREATE", "foia_request", saved.getId(),
            actor, saved.getAgencyId());

        log.info("foia_request created id={} agencyId={} correlationId=N/A",
            saved.getId(), saved.getAgencyId());

        return saved;
    }

    public Optional<FoiaRequest> findById(String id) {
        return repo.findById(id);
    }

    /**
     * ⚠ Item 10 — returns foia_requests across ALL agencies. The
     * {@code findByAgencyId} method exists on the repository but isn't
     * called from anywhere.
     */
    public List<FoiaRequest> listAll() {
        return repo.findAll();
    }

    public Optional<FoiaRequest> update(String id, FoiaRequestCreateRequest req, String actor) {
        return repo.findById(id).map(s -> {
            s.setTitle(req.getTitle());
            // ⚠ Item 9.
            s.setDescription(req.getDescription());
            if (req.getStatus() != null) s.setStatus(req.getStatus());
            s.setUpdatedAt(Instant.now());
            FoiaRequest saved = repo.save(s);
            auditLogger.recordAsync("UPDATE", "foia_request", saved.getId(),
                actor, saved.getAgencyId());
            return saved;
        });
    }

    public boolean delete(String id, String actor) {
        return repo.findById(id).map(s -> {
            repo.deleteById(id);
            auditLogger.recordAsync("DELETE", "foia_request", id, actor, s.getAgencyId());
            return true;
        }).orElse(false);
    }

    /**
     * Transition DRAFT/INTERNAL_REVIEW/READY_TO_PUBLISH -> PUBLISHED.
     * FAR 5.203 publication. ⚠ Item 2 — publish event audit-logged async.
     */
    public Optional<FoiaRequest> publish(String id, String actor) {
        return repo.findById(id).map(s -> {
            s.setStatus("PUBLISHED");
            s.setPostedAt(Instant.now());
            s.setUpdatedAt(Instant.now());
            FoiaRequest saved = repo.save(s);
            // ⚠ Item 2.
            auditLogger.recordAsync("PUBLISH", "foia_request", saved.getId(),
                actor, saved.getAgencyId());
            log.info("foia_request published id={} agencyId={}",
                saved.getId(), saved.getAgencyId());
            return saved;
        });
    }

    public Optional<FoiaRequest> cancel(String id, String actor) {
        return repo.findById(id).map(s -> {
            s.setStatus("CANCELLED");
            s.setUpdatedAt(Instant.now());
            FoiaRequest saved = repo.save(s);
            // ⚠ Item 2.
            auditLogger.recordAsync("CANCEL", "foia_request", saved.getId(),
                actor, saved.getAgencyId());
            return saved;
        });
    }
}
