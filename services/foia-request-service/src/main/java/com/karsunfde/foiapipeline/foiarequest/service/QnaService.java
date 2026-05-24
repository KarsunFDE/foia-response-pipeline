package com.karsunfde.foiapipeline.foia_request.service;

import com.karsunfde.foiapipeline.foia_request.audit.AuditLogger;
import com.karsunfde.foiapipeline.foia_request.dto.QnaAnswerRequest;
import com.karsunfde.foiapipeline.foia_request.dto.QnaRequest;
import com.karsunfde.foiapipeline.foia_request.model.Qna;
import com.karsunfde.foiapipeline.foia_request.model.FoiaRequest;
import com.karsunfde.foiapipeline.foia_request.repository.QnaRepository;
import com.karsunfde.foiapipeline.foia_request.repository.FoiaRequestRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.List;
import java.util.Optional;

/**
 * Vendor Q&A workflow.
 *
 * Brownfield-debt items present here:
 *   - Item 2 — Q&A state transitions audit-logged via recordAsync.
 *   - Item 9 — question + answer stored verbatim; both feed the
 *     ai-orchestrator /answer-qa prompt.
 *   - Item 10 — listForFoiaRequest does not re-check agency.
 */
@Service
public class QnaService {

    private static final Logger log = LoggerFactory.getLogger(QnaService.class);

    private final QnaRepository repo;
    private final FoiaRequestRepository solRepo;
    private final AuditLogger auditLogger;

    @Autowired
    public QnaService(QnaRepository repo, FoiaRequestRepository solRepo, AuditLogger auditLogger) {
        this.repo = repo;
        this.solRepo = solRepo;
        this.auditLogger = auditLogger;
    }

    public Optional<Qna> submit(String foia_requestId, QnaRequest req, String actor) {
        Optional<FoiaRequest> solOpt = solRepo.findById(foia_requestId);
        if (solOpt.isEmpty()) return Optional.empty();
        FoiaRequest sol = solOpt.get();

        Qna q = new Qna();
        q.setFoiaRequestId(foia_requestId);
        q.setAgencyId(sol.getAgencyId());
        // ⚠ Item 9 — raw HTML accepted.
        q.setQuestion(req.getQuestion());
        q.setVendorId(req.getVendorId());
        q.setStatus("SUBMITTED");
        q.setSubmittedAt(Instant.now());
        Qna saved = repo.save(q);

        // ⚠ Item 2 — fire-and-forget.
        auditLogger.recordAsync("QNA_SUBMIT", "qna", saved.getId(), actor, sol.getAgencyId());

        log.info("qna submitted foia_requestId={} vendorId={}", foia_requestId, req.getVendorId());
        return Optional.of(saved);
    }

    public Optional<Qna> answer(String qnaId, QnaAnswerRequest req, String actor) {
        return repo.findById(qnaId).map(q -> {
            // ⚠ Item 9.
            q.setAnswer(req.getAnswer());
            q.setStatus("PUBLISHED");
            q.setAnsweredAt(Instant.now());
            Qna saved = repo.save(q);
            // ⚠ Item 2.
            auditLogger.recordAsync("QNA_ANSWER", "qna", saved.getId(), actor, q.getAgencyId());
            return saved;
        });
    }

    public List<Qna> listForFoiaRequest(String foia_requestId) {
        // ⚠ Item 10 — does not re-check caller agency.
        return repo.findByFoiaRequestId(foia_requestId);
    }
}
