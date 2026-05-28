package com.karsunfde.foiapipeline.foiarequest.dto;

/**
 * Create-FOIA-request request DTO (5 USC 552).
 *
 * ⚠ DELIBERATE — Item 9:
 *   No {@code @SafeHtml}, no {@code @NotBlank}, no length cap on
 *   {@code recordsSought} / {@code description}. The fields accept
 *   {@code <script>} tags verbatim. Cohort fixes in W4 Wed AI Security
 *   Engineering Day. The inverted threat model (untrusted requester) makes
 *   this especially live.
 *
 * ⚠ DELIBERATE — Item 10 reinforcement:
 *   {@code agencyId} is on the DTO but the controller doesn't cross-check it
 *   against the JWT's agency claim.
 *
 * NOTE: legacy {@code description} accessor retained so the inherited
 * acquisition components/controllers compile; FOIA flows use
 * {@code recordsSought}.
 */
public class FoiaRequestCreateRequest {

    private String agencyId;
    private String title;
    private String recordsSought; // ⚠ raw HTML accepted (Item 9)
    private String status;

    // — Requester (inverted threat model: external, untrusted) —
    private String requesterName;
    private String requesterOrg;
    private String requesterType;

    // — Fee + processing posture —
    private String feeCategory;
    private boolean feeWaiverRequested;
    private boolean expeditedProcessingRequested;
    private String expeditedJustification;

    /** ⚠ LEGACY (acquisition-era) — raw HTML accepted (Item 9). */
    private String description;

    public FoiaRequestCreateRequest() {}

    public String getAgencyId() { return agencyId; }
    public void setAgencyId(String agencyId) { this.agencyId = agencyId; }
    public String getTitle() { return title; }
    public void setTitle(String title) { this.title = title; }
    public String getRecordsSought() { return recordsSought; }
    public void setRecordsSought(String recordsSought) { this.recordsSought = recordsSought; }
    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }

    public String getRequesterName() { return requesterName; }
    public void setRequesterName(String requesterName) { this.requesterName = requesterName; }
    public String getRequesterOrg() { return requesterOrg; }
    public void setRequesterOrg(String requesterOrg) { this.requesterOrg = requesterOrg; }
    public String getRequesterType() { return requesterType; }
    public void setRequesterType(String requesterType) { this.requesterType = requesterType; }

    public String getFeeCategory() { return feeCategory; }
    public void setFeeCategory(String feeCategory) { this.feeCategory = feeCategory; }
    public boolean isFeeWaiverRequested() { return feeWaiverRequested; }
    public void setFeeWaiverRequested(boolean feeWaiverRequested) { this.feeWaiverRequested = feeWaiverRequested; }
    public boolean isExpeditedProcessingRequested() { return expeditedProcessingRequested; }
    public void setExpeditedProcessingRequested(boolean expeditedProcessingRequested) { this.expeditedProcessingRequested = expeditedProcessingRequested; }
    public String getExpeditedJustification() { return expeditedJustification; }
    public void setExpeditedJustification(String expeditedJustification) { this.expeditedJustification = expeditedJustification; }

    /** ⚠ LEGACY accessor (inherited acquisition components). */
    public String getDescription() { return description; }
    public void setDescription(String description) { this.description = description; }
}
