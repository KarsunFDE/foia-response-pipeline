package com.karsunfde.foiapipeline.foiarequest.controller;

import com.karsunfde.foiapipeline.foiarequest.dto.AmendmentRequest;
import com.karsunfde.foiapipeline.foiarequest.dto.ProposalSubmitRequest;
import com.karsunfde.foiapipeline.foiarequest.dto.QnaAnswerRequest;
import com.karsunfde.foiapipeline.foiarequest.dto.QnaRequest;
import com.karsunfde.foiapipeline.foiarequest.dto.FoiaRequestCreateRequest;
import com.karsunfde.foiapipeline.foiarequest.model.Amendment;
import com.karsunfde.foiapipeline.foiarequest.model.Proposal;
import com.karsunfde.foiapipeline.foiarequest.model.Qna;
import com.karsunfde.foiapipeline.foiarequest.model.FoiaRequest;
import com.karsunfde.foiapipeline.foiarequest.service.AmendmentService;
import com.karsunfde.foiapipeline.foiarequest.service.ProposalService;
import com.karsunfde.foiapipeline.foiarequest.service.QnaService;
import com.karsunfde.foiapipeline.foiarequest.service.FoiaRequestService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * FoiaRequest REST surface — covers Workflow 1 (drafting → publication),
 * Workflow 2 (Q&A + amendments), Workflow 3 (proposal intake).
 *
 * Endpoints (feature-inventory-target.md, foia-request-service rows):
 *   POST    /api/foia-requests
 *   GET     /api/foia-requests
 *   GET     /api/foia-requests/{id}
 *   PUT     /api/foia-requests/{id}
 *   DELETE  /api/foia-requests/{id}
 *   POST    /api/foia-requests/{id}/publish
 *   POST    /api/foia-requests/{id}/cancel
 *   POST    /api/foia-requests/{id}/amendments
 *   GET     /api/foia-requests/{id}/amendments
 *   POST    /api/foia-requests/{id}/qa
 *   PUT     /api/foia-requests/{id}/qa/{qnaId}/answer
 *   GET     /api/foia-requests/{id}/qa
 *   POST    /api/foia-requests/{id}/proposals
 *   GET     /api/foia-requests/{id}/proposals
 *   POST    /api/foia-requests/{id}/proposals/{pid}/acknowledge-amendment
 */
@RestController
@RequestMapping("/api/foia-requests")
public class FoiaRequestController {

    private final FoiaRequestService svc;
    private final AmendmentService amendmentSvc;
    private final QnaService qnaSvc;
    private final ProposalService proposalSvc;

    @Autowired
    public FoiaRequestController(FoiaRequestService svc,
                                  AmendmentService amendmentSvc,
                                  QnaService qnaSvc,
                                  ProposalService proposalSvc) {
        this.svc = svc;
        this.amendmentSvc = amendmentSvc;
        this.qnaSvc = qnaSvc;
        this.proposalSvc = proposalSvc;
    }

    @GetMapping
    public List<FoiaRequest> list(@RequestHeader(value = "X-User", defaultValue = "anonymous") String actor) {
        // ⚠ Item 10 — does not filter by agency.
        return svc.listAll();
    }

    @GetMapping("/{id}")
    public ResponseEntity<FoiaRequest> get(@PathVariable String id) {
        return svc.findById(id)
            .map(ResponseEntity::ok)
            .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping
    public ResponseEntity<FoiaRequest> create(
            @RequestBody FoiaRequestCreateRequest req,
            @RequestHeader(value = "X-User", defaultValue = "anonymous") String actor) {
        // ⚠ Item 9 — no validation on req.description.
        FoiaRequest created = svc.create(req, actor);
        return ResponseEntity.ok(created);
    }

    @PutMapping("/{id}")
    public ResponseEntity<FoiaRequest> update(
            @PathVariable String id,
            @RequestBody FoiaRequestCreateRequest req,
            @RequestHeader(value = "X-User", defaultValue = "anonymous") String actor) {
        return svc.update(id, req, actor)
            .map(ResponseEntity::ok)
            .orElse(ResponseEntity.notFound().build());
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> delete(
            @PathVariable String id,
            @RequestHeader(value = "X-User", defaultValue = "anonymous") String actor) {
        boolean ok = svc.delete(id, actor);
        return ok ? ResponseEntity.noContent().build() : ResponseEntity.notFound().build();
    }

    // -------- State machine transitions (Workflow 1) --------

    @PostMapping("/{id}/publish")
    public ResponseEntity<FoiaRequest> publish(
            @PathVariable String id,
            @RequestHeader(value = "X-User", defaultValue = "anonymous") String actor) {
        return svc.publish(id, actor)
            .map(ResponseEntity::ok)
            .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping("/{id}/cancel")
    public ResponseEntity<FoiaRequest> cancel(
            @PathVariable String id,
            @RequestHeader(value = "X-User", defaultValue = "anonymous") String actor) {
        return svc.cancel(id, actor)
            .map(ResponseEntity::ok)
            .orElse(ResponseEntity.notFound().build());
    }

    // -------- Amendments (Workflow 2 — FAR 15.206) --------

    @PostMapping("/{id}/amendments")
    public ResponseEntity<Amendment> issueAmendment(
            @PathVariable String id,
            @RequestBody AmendmentRequest req,
            @RequestHeader(value = "X-User", defaultValue = "anonymous") String actor) {
        return amendmentSvc.issue(id, req, actor)
            .map(ResponseEntity::ok)
            .orElse(ResponseEntity.notFound().build());
    }

    @GetMapping("/{id}/amendments")
    public List<Amendment> listAmendments(@PathVariable String id) {
        // ⚠ Item 10 — does not re-check caller agency.
        return amendmentSvc.listForFoiaRequest(id);
    }

    // -------- Q&A (Workflow 2) --------

    @PostMapping("/{id}/qa")
    public ResponseEntity<Qna> submitQuestion(
            @PathVariable String id,
            @RequestBody QnaRequest req,
            @RequestHeader(value = "X-User", defaultValue = "anonymous") String actor) {
        return qnaSvc.submit(id, req, actor)
            .map(ResponseEntity::ok)
            .orElse(ResponseEntity.notFound().build());
    }

    @PutMapping("/{id}/qa/{qnaId}/answer")
    public ResponseEntity<Qna> answer(
            @PathVariable String id,
            @PathVariable String qnaId,
            @RequestBody QnaAnswerRequest req,
            @RequestHeader(value = "X-User", defaultValue = "anonymous") String actor) {
        return qnaSvc.answer(qnaId, req, actor)
            .map(ResponseEntity::ok)
            .orElse(ResponseEntity.notFound().build());
    }

    @GetMapping("/{id}/qa")
    public List<Qna> listQna(@PathVariable String id) {
        // ⚠ Item 10 — vendor should only see their own pre-publish entries.
        return qnaSvc.listForFoiaRequest(id);
    }

    // -------- Proposal intake (Workflow 3) --------

    @PostMapping("/{id}/proposals")
    public ResponseEntity<Proposal> submitProposal(
            @PathVariable String id,
            @RequestBody ProposalSubmitRequest req,
            @RequestHeader(value = "X-User", defaultValue = "anonymous") String actor) {
        return proposalSvc.submit(id, req, actor)
            .map(ResponseEntity::ok)
            .orElse(ResponseEntity.notFound().build());
    }

    @GetMapping("/{id}/proposals")
    public List<Proposal> listProposals(@PathVariable String id) {
        // ⚠ Item 2 — must be gated on post-deadline + audit-logged on view.
        // ⚠ Item 10 — does not re-check caller agency.
        return proposalSvc.listForFoiaRequest(id);
    }

    @PostMapping("/{id}/proposals/{pid}/acknowledge-amendment")
    public ResponseEntity<Proposal> acknowledgeAmendment(
            @PathVariable String id,
            @PathVariable("pid") String proposalId,
            @RequestParam("amendmentNumber") int amendmentNumber,
            @RequestHeader(value = "X-User", defaultValue = "anonymous") String actor) {
        return proposalSvc.acknowledgeAmendment(proposalId, amendmentNumber, actor)
            .map(ResponseEntity::ok)
            .orElse(ResponseEntity.notFound().build());
    }
}
