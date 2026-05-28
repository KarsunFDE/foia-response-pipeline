package com.karsunfde.foiapipeline.foiarequest.model;

import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.Instant;
import java.util.HashMap;
import java.util.Map;

/**
 * FoiaRequest document — a Freedom of Information Act request (5 USC 552).
 *
 * Domain reshape from the acquire-gov Solicitation baseline: the FOIA shape
 * is requester + records-sought + fee posture + expedited posture, governed
 * by a statutory 20-working-day response clock (5 USC 552(a)(6)(A)). The
 * threat model is INVERTED — the requester is an external, potentially
 * adversarial party.
 *
 * ⚠ DELIBERATE — Item 10:
 *   {@code agencyId} is in the schema (so the data is multi-tenant-shaped)
 *   but the repository does not filter on it. Cohort fixes in W2 Wed
 *   multi-tenant retrieval-boundary work.
 *
 * ⚠ DELIBERATE — Item 9:
 *   {@code recordsSought} / {@code description} are not sanitized; arbitrary
 *   HTML accepted on write and returned verbatim on read. Cohort fixes in
 *   W4 Wed AI Security Engineering Day (prompt-injection-via-stored-content
 *   — the records-sought text feeds the ai-orchestrator prompt; the inverted
 *   threat model makes this especially live).
 *
 * State machine (FOIA processing):
 *   INTAKE_TRIAGE -> EXEMPTION_ANALYSIS -> REDACTION_PROPOSAL -> HITL_REVIEW
 *     -> RESPONSE -> (APPEAL) -> CLOSED
 *
 * NOTE: the legacy acquisition fields ({@code naics}, {@code setAside},
 * {@code sections}, {@code postedAt}, {@code closingAt}) and their accessors
 * remain so the inherited acquisition components/controllers compile. They
 * are NOT part of the FOIA shape; the pair repurposes/removes them W4–W5.
 */
@Document(collection = "foia_requests")
public class FoiaRequest {

    @Id
    private String id;

    /** ⚠ Item 10 — present but un-enforced. */
    private String agencyId;

    /** Public tracking number assigned at intake (FOIA.gov convention). */
    private String trackingNumber;

    private String title;

    /** Free-text description of the records sought. ⚠ Item 9 — accepts arbitrary HTML. */
    private String recordsSought;

    private String status;

    // --- Requester (inverted threat model: external, untrusted) ---
    private String requesterName;
    private String requesterOrg;
    /** commercial | news_media_educational_scientific | other. */
    private String requesterType;

    // --- Records scope ---
    private Instant dateRangeStart;
    private Instant dateRangeEnd;

    // --- Fee + processing posture ---
    /** Derived from requesterType (5 USC 552(a)(4)(A)). */
    private String feeCategory;
    private boolean feeWaiverRequested;
    private boolean expeditedProcessingRequested;
    private String expeditedJustification;

    // --- Statutory clock (5 USC 552(a)(6)(A)) ---
    /** Starts the 20-working-day clock. */
    private Instant receivedDate;
    /** receivedDate + 20 working days (+10 unusual circumstances). */
    private Instant dueDate;

    /** full_grant | partial_grant | full_denial | no_records. */
    private String disposition;

    /** ⚠ LEGACY (acquisition-era) — kept un-sanitized to preserve Item 9. */
    private String description;
    /** ⚠ LEGACY. */
    private String naics;
    /** ⚠ LEGACY. */
    private String setAside;
    /** ⚠ LEGACY — values unsanitized (Item 9). */
    private Map<String, String> sections = new HashMap<>();
    /** ⚠ LEGACY. */
    private Instant postedAt;
    /** ⚠ LEGACY. */
    private Instant closingAt;

    private Instant createdAt;
    private Instant updatedAt;

    public FoiaRequest() {}

    // --- getters / setters ---

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }

    public String getAgencyId() { return agencyId; }
    public void setAgencyId(String agencyId) { this.agencyId = agencyId; }

    public String getTrackingNumber() { return trackingNumber; }
    public void setTrackingNumber(String trackingNumber) { this.trackingNumber = trackingNumber; }

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

    public Instant getDateRangeStart() { return dateRangeStart; }
    public void setDateRangeStart(Instant dateRangeStart) { this.dateRangeStart = dateRangeStart; }

    public Instant getDateRangeEnd() { return dateRangeEnd; }
    public void setDateRangeEnd(Instant dateRangeEnd) { this.dateRangeEnd = dateRangeEnd; }

    public String getFeeCategory() { return feeCategory; }
    public void setFeeCategory(String feeCategory) { this.feeCategory = feeCategory; }

    public boolean isFeeWaiverRequested() { return feeWaiverRequested; }
    public void setFeeWaiverRequested(boolean feeWaiverRequested) { this.feeWaiverRequested = feeWaiverRequested; }

    public boolean isExpeditedProcessingRequested() { return expeditedProcessingRequested; }
    public void setExpeditedProcessingRequested(boolean expeditedProcessingRequested) { this.expeditedProcessingRequested = expeditedProcessingRequested; }

    public String getExpeditedJustification() { return expeditedJustification; }
    public void setExpeditedJustification(String expeditedJustification) { this.expeditedJustification = expeditedJustification; }

    public Instant getReceivedDate() { return receivedDate; }
    public void setReceivedDate(Instant receivedDate) { this.receivedDate = receivedDate; }

    public Instant getDueDate() { return dueDate; }
    public void setDueDate(Instant dueDate) { this.dueDate = dueDate; }

    public String getDisposition() { return disposition; }
    public void setDisposition(String disposition) { this.disposition = disposition; }

    // --- LEGACY accessors (inherited acquisition components) ---

    public String getDescription() { return description; }
    public void setDescription(String description) { this.description = description; }

    public String getNaics() { return naics; }
    public void setNaics(String naics) { this.naics = naics; }

    public String getSetAside() { return setAside; }
    public void setSetAside(String setAside) { this.setAside = setAside; }

    public Map<String, String> getSections() { return sections; }
    public void setSections(Map<String, String> sections) { this.sections = sections; }

    public Instant getPostedAt() { return postedAt; }
    public void setPostedAt(Instant postedAt) { this.postedAt = postedAt; }

    public Instant getClosingAt() { return closingAt; }
    public void setClosingAt(Instant closingAt) { this.closingAt = closingAt; }

    public Instant getCreatedAt() { return createdAt; }
    public void setCreatedAt(Instant createdAt) { this.createdAt = createdAt; }

    public Instant getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(Instant updatedAt) { this.updatedAt = updatedAt; }
}
