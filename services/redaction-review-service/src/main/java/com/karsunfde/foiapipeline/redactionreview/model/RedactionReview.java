package com.karsunfde.foiapipeline.redactionreview.model;

import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;

/**
 * RedactionReview record — exemption analysis + redaction proposal/review for
 * a FOIA request (5 USC 552(b), 28 CFR 16.6).
 *
 * Domain reshape from the acquire-gov Evaluation (TEP) baseline. A redaction
 * review proposes exemptions over a responsive document, records the
 * rationale, and produces a release/withhold determination that is HITL-gated
 * because release is irreversible. A denial / partial grant is appealable.
 *
 * State (FOIA): PROPOSED → UNDER_REVIEW → APPROVED_FOR_RELEASE / WITHHELD.
 *
 * ⚠ Item 3 — fetching responsive-document text for review is the canonical
 * reproducer for the no-circuit-breaker debt (review → foia-request-service
 * hot loop).
 *
 * NOTE: the legacy TEP fields ({@code panelMembers}, {@code factorIds},
 * {@code consensusAt}, {@code ssddDocId}) and the legacy {@code state}
 * values remain so the inherited redaction-review-service flow + AwardService
 * compile. The pair repurposes/removes them W4–W5. FOIA flows use the
 * exemption + release-decision fields added below.
 */
@Document(collection = "redaction_reviews")
public class RedactionReview {

    @Id
    private String id;

    private String foiaRequestId;
    private String agencyId;
    private String state;

    // --- FOIA exemption / redaction shape ---
    /** Reference to the responsive document under review. */
    private String documentRef;
    /** Exemptions claimed: (b)(1)…(b)(9). */
    private List<String> proposedExemptions = new ArrayList<>();
    /** Why each segment is withheld (deliberative / privacy / law-enforcement basis). */
    private String redactionRationale;
    /** foia_officer | general_counsel | records_custodian. */
    private String reviewerRole;
    /** release_full | release_partial | withhold (irreversible — HITL-gated). */
    private String releaseDecision;
    /** A denial / partial grant is appealable by the requester. */
    private boolean appealable;
    private Instant decidedAt;

    // --- LEGACY (acquisition-era TEP) ---
    private List<String> panelMembers = new ArrayList<>();
    private List<String> factorIds = new ArrayList<>();
    private Instant consensusAt;
    private String ssddDocId;

    private Instant createdAt;

    public RedactionReview() {}

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }
    public String getFoiaRequestId() { return foiaRequestId; }
    public void setFoiaRequestId(String foiaRequestId) { this.foiaRequestId = foiaRequestId; }
    public String getAgencyId() { return agencyId; }
    public void setAgencyId(String agencyId) { this.agencyId = agencyId; }
    public String getState() { return state; }
    public void setState(String state) { this.state = state; }

    // --- FOIA accessors ---
    public String getDocumentRef() { return documentRef; }
    public void setDocumentRef(String documentRef) { this.documentRef = documentRef; }
    public List<String> getProposedExemptions() { return proposedExemptions; }
    public void setProposedExemptions(List<String> proposedExemptions) { this.proposedExemptions = proposedExemptions; }
    public String getRedactionRationale() { return redactionRationale; }
    public void setRedactionRationale(String redactionRationale) { this.redactionRationale = redactionRationale; }
    public String getReviewerRole() { return reviewerRole; }
    public void setReviewerRole(String reviewerRole) { this.reviewerRole = reviewerRole; }
    public String getReleaseDecision() { return releaseDecision; }
    public void setReleaseDecision(String releaseDecision) { this.releaseDecision = releaseDecision; }
    public boolean isAppealable() { return appealable; }
    public void setAppealable(boolean appealable) { this.appealable = appealable; }
    public Instant getDecidedAt() { return decidedAt; }
    public void setDecidedAt(Instant decidedAt) { this.decidedAt = decidedAt; }

    // --- LEGACY accessors (inherited acquisition flow) ---
    public List<String> getPanelMembers() { return panelMembers; }
    public void setPanelMembers(List<String> panelMembers) { this.panelMembers = panelMembers; }
    public List<String> getFactorIds() { return factorIds; }
    public void setFactorIds(List<String> factorIds) { this.factorIds = factorIds; }
    public Instant getCreatedAt() { return createdAt; }
    public void setCreatedAt(Instant createdAt) { this.createdAt = createdAt; }
    public Instant getConsensusAt() { return consensusAt; }
    public void setConsensusAt(Instant consensusAt) { this.consensusAt = consensusAt; }
    public String getSsddDocId() { return ssddDocId; }
    public void setSsddDocId(String ssddDocId) { this.ssddDocId = ssddDocId; }
}
