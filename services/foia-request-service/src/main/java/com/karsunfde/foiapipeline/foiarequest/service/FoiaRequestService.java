package com.karsunfde.foiapipeline.foiarequest.service;

import com.karsunfde.foiapipeline.foiarequest.audit.AuditLogger;
import com.karsunfde.foiapipeline.foiarequest.dto.FoiaRequestCreateRequest;
import com.karsunfde.foiapipeline.foiarequest.model.FoiaRequest;
import com.karsunfde.foiapipeline.foiarequest.repository.FoiaRequestRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.List;
import java.util.Optional;

/**
 * FoiaRequest business logic (5 USC 552 processing).
 *
 * State machine:
 *   INTAKE_TRIAGE -> EXEMPTION_ANALYSIS -> REDACTION_PROPOSAL -> HITL_REVIEW
 *     -> RESPONSE -> (APPEAL) -> CLOSED
 *   The 20-working-day statutory clock starts at intake (create()).
 *
 * Brownfield-debt items present in this class:
 *   - Item 2 — {@link AuditLogger#recordAsync} runs after response flushes.
 *   - Item 9 — description / recordsSought stored verbatim (no Jsoup.clean).
 *   - Item 10 — listAll calls repo.findAll() not findByAgencyId.
 *
 * NOTE: the legacy publish()/cancel() transitions remain for the inherited
 * acquisition controllers; FOIA transitions are status updates via update().
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
        // ⚠ Item 9 — no Jsoup.clean, no escape, no length cap (legacy description
        // passthrough — the locked Item-9 test asserts on this field).
        s.setDescription(req.getDescription());
        // ⚠ Item 9 — records-sought carries the same un-sanitized-text debt;
        // it feeds the ai-orchestrator prompt (prompt-injection-via-stored-content).
        s.setRecordsSought(req.getRecordsSought());
        s.setRequesterName(req.getRequesterName());
        s.setRequesterOrg(req.getRequesterOrg());
        s.setRequesterType(req.getRequesterType());
        s.setFeeCategory(req.getFeeCategory());
        s.setFeeWaiverRequested(req.isFeeWaiverRequested());
        s.setExpeditedProcessingRequested(req.isExpeditedProcessingRequested());
        s.setExpeditedJustification(req.getExpeditedJustification());
        s.setStatus(req.getStatus() != null ? req.getStatus() : "INTAKE_TRIAGE");

        // Statutory 20-working-day clock (5 USC 552(a)(6)(A)) starts at intake.
        Instant received = Instant.now();
        s.setReceivedDate(received);
        s.setDueDate(plusWorkingDays(received, 20));

        s.setCreatedAt(Instant.now());
        s.setUpdatedAt(Instant.now());

        FoiaRequest saved = repo.save(s);

        // ⚠ Item 2 — fire-and-forget. Returns immediately, controller flushes
        //   response, audit may or may not land.
        auditLogger.recordAsync("CREATE", "foiaRequest", saved.getId(),
            actor, saved.getAgencyId());

        log.info("foiaRequest created id={} agencyId={} correlationId=N/A",
            saved.getId(), saved.getAgencyId());

        return saved;
    }

    public Optional<FoiaRequest> findById(String id) {
        return repo.findById(id);
    }

    /**
     * ⚠ Item 10 — returns foiaRequests across ALL agencies. The
     * {@code findByAgencyId} method exists on the repository but isn't
     * called from anywhere.
     */
    public List<FoiaRequest> listAll() {
        return repo.findAll();
    }

    public Optional<FoiaRequest> update(String id, FoiaRequestCreateRequest req, String actor) {
        return repo.findById(id).map(s -> {
            s.setTitle(req.getTitle());
            // ⚠ Item 9 (legacy description passthrough — locked test asserts here).
            s.setDescription(req.getDescription());
            // ⚠ Item 9 — records-sought same un-sanitized debt.
            if (req.getRecordsSought() != null) s.setRecordsSought(req.getRecordsSought());
            if (req.getRequesterName() != null) s.setRequesterName(req.getRequesterName());
            if (req.getRequesterOrg() != null) s.setRequesterOrg(req.getRequesterOrg());
            if (req.getRequesterType() != null) s.setRequesterType(req.getRequesterType());
            if (req.getFeeCategory() != null) s.setFeeCategory(req.getFeeCategory());
            s.setFeeWaiverRequested(req.isFeeWaiverRequested());
            s.setExpeditedProcessingRequested(req.isExpeditedProcessingRequested());
            if (req.getExpeditedJustification() != null) s.setExpeditedJustification(req.getExpeditedJustification());
            if (req.getStatus() != null) s.setStatus(req.getStatus());
            s.setUpdatedAt(Instant.now());
            FoiaRequest saved = repo.save(s);
            auditLogger.recordAsync("UPDATE", "foiaRequest", saved.getId(),
                actor, saved.getAgencyId());
            return saved;
        });
    }

    /**
     * Add {@code n} working days (Mon–Fri; holidays ignored) to {@code from}.
     * Approximates the FOIA 20-working-day clock (5 USC 552(a)(6)(A)).
     */
    static Instant plusWorkingDays(Instant from, int n) {
        java.time.ZonedDateTime z = from.atZone(java.time.ZoneOffset.UTC);
        int added = 0;
        while (added < n) {
            z = z.plusDays(1);
            java.time.DayOfWeek d = z.getDayOfWeek();
            if (d != java.time.DayOfWeek.SATURDAY && d != java.time.DayOfWeek.SUNDAY) {
                added++;
            }
        }
        return z.toInstant();
    }

    public boolean delete(String id, String actor) {
        return repo.findById(id).map(s -> {
            repo.deleteById(id);
            auditLogger.recordAsync("DELETE", "foiaRequest", id, actor, s.getAgencyId());
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
            auditLogger.recordAsync("PUBLISH", "foiaRequest", saved.getId(),
                actor, saved.getAgencyId());
            log.info("foiaRequest published id={} agencyId={}",
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
            auditLogger.recordAsync("CANCEL", "foiaRequest", saved.getId(),
                actor, saved.getAgencyId());
            return saved;
        });
    }
}
