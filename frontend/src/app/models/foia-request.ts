/**
 * FoiaRequest — a Freedom of Information Act request (5 USC 552).
 *
 * Domain reshape from the acquire-gov Solicitation baseline: a FOIA request
 * is intake-driven (requester identity + records sought + fee posture +
 * expedited posture) and governed by a statutory 20-working-day response
 * clock (5 USC 552(a)(6)(A)). The threat model is INVERTED — the requester
 * is an external, potentially adversarial party.
 *
 * NOTE on legacy fields: a handful of acquisition-era optional fields
 * (`naics`, `setAside`, `contractType`, `ceilingValue`, `noticeType`,
 * `sections`, `proposalsDueAt`) remain on the interface. They are the raw
 * material the pair repurposes/deletes across the inherited acquisition
 * components in W4–W5 (per domain-mapping.md §"Additional inherited
 * entities"). They are NOT part of the FOIA shape — do not author new
 * FOIA flows against them.
 */

/** Requester category — drives the FOIA fee category (5 USC 552(a)(4)(A)). */
export type RequesterType =
  | 'commercial'
  | 'news_media_educational_scientific'
  | 'other';

/** Derived fee category per requester type (5 USC 552(a)(4)(A)(ii)). */
export type FeeCategory =
  | 'commercial'                          // search + review + duplication
  | 'news_media_educational_scientific'   // duplication after first 100 pages
  | 'other';                              // search after 2h + dup after 100 pages

/** Final disposition of a FOIA request (DOJ annual-report categories). */
export type FoiaDisposition =
  | 'full_grant'
  | 'partial_grant'
  | 'full_denial'
  | 'no_records';

export interface FoiaRequest {
  id: string;
  /** Owning agency / component (tenant boundary — Item 10 surface). */
  agencyId: string;
  /** Public tracking number assigned at intake (FOIA.gov convention). */
  trackingNumber?: string;
  /** Short subject line for the request. */
  title: string;
  /** Free-text description of the records sought (replaces Section C SOW). */
  recordsSought: string;
  /** Workflow status — see FoiaRequestState. */
  status: string;

  // — Requester identity (inverted threat model: external, untrusted) —
  requesterName?: string;
  requesterOrg?: string;
  requesterType?: RequesterType;

  // — Records scope —
  dateRangeStart?: string;   // ISO date
  dateRangeEnd?: string;     // ISO date

  // — Fee + processing posture —
  /** Derived from requesterType (5 USC 552(a)(4)(A)). */
  feeCategory?: FeeCategory;
  feeWaiverRequested?: boolean;
  expeditedProcessingRequested?: boolean;
  /** Justification supplied when expedited processing is requested. */
  expeditedJustification?: string;

  // — Statutory clock (5 USC 552(a)(6)(A)) —
  /** Date the request was received — starts the 20-working-day clock. */
  receivedDate?: string;
  /** receivedDate + 20 working days (+10 for unusual circumstances). */
  dueDate?: string;

  /** Final disposition once the response is issued. */
  disposition?: FoiaDisposition;

  createdAt?: string;
  updatedAt?: string;

  /**
   * ⚠ LEGACY (acquisition-era) — repurposed/deleted by the pair in W4–W5.
   * Kept optional so the inherited acquisition components still compile.
   */
  description?: string;
  naics?: string;
  setAside?: '' | 'SDVOSB' | 'WOSB' | 'HUBZONE' | '8A' | 'SMALL_BUSINESS' | 'FULL_AND_OPEN';
  contractType?: 'FFP' | 'CPFF' | 'T_AND_M' | 'IDIQ' | 'BPA';
  ceilingValue?: number;
  noticeType?: 'RFI' | 'SOURCES_SOUGHT' | 'RFP' | 'RFQ' | 'COMBINED_SYNOPSIS';
  sections?: FoiaRequestSections;
  proposalsDueAt?: string;
}

/**
 * ⚠ LEGACY (acquisition-era FAR 15.204 Section A–M). Retained only so the
 * inherited acquisition components compile; not part of the FOIA shape.
 */
export interface FoiaRequestSections {
  sectionA?: string;
  sectionB?: string;
  sectionC?: string;
  sectionD?: string;
  sectionE?: string;
  sectionF?: string;
  sectionG?: string;
  sectionH?: string;
  sectionJ?: string;
  sectionK?: string;
  sectionL?: string;
  sectionM?: string;
}

export interface FoiaRequestCreate {
  agencyId: string;
  title: string;
  recordsSought: string;
  status?: string;
  requesterName?: string;
  requesterOrg?: string;
  requesterType?: RequesterType;
  dateRangeStart?: string;
  dateRangeEnd?: string;
  feeCategory?: FeeCategory;
  feeWaiverRequested?: boolean;
  expeditedProcessingRequested?: boolean;
  expeditedJustification?: string;
  receivedDate?: string;
  dueDate?: string;

  // ⚠ LEGACY — see FoiaRequest above.
  description?: string;
  naics?: string;
  setAside?: string;
  contractType?: string;
  ceilingValue?: number;
  noticeType?: string;
  sections?: FoiaRequestSections;
  proposalsDueAt?: string;
}

/**
 * FOIA processing workflow (replaces the solicitation publication lifecycle).
 *   INTAKE_TRIAGE -> EXEMPTION_ANALYSIS -> REDACTION_PROPOSAL -> HITL_REVIEW
 *     -> RESPONSE -> (APPEAL)
 */
export type FoiaRequestState =
  | 'INTAKE_TRIAGE'
  | 'EXEMPTION_ANALYSIS'
  | 'REDACTION_PROPOSAL'
  | 'HITL_REVIEW'
  | 'RESPONSE'
  | 'APPEAL'
  | 'CLOSED';

/**
 * The nine FOIA exemptions (5 USC 552(b)(1)–(b)(9)). Used by RedactionReview.
 */
export type FoiaExemption =
  | '(b)(1)'   // classified national defense / foreign policy
  | '(b)(2)'   // internal personnel rules and practices
  | '(b)(3)'   // prohibited from disclosure by another statute
  | '(b)(4)'   // trade secrets / privileged or confidential commercial info
  | '(b)(5)'   // privileged inter/intra-agency comms (deliberative process)
  | '(b)(6)'   // personal privacy
  | '(b)(7)'   // law-enforcement records
  | '(b)(8)'   // financial-institution supervision
  | '(b)(9)';  // geological / geophysical / well data

export const FOIA_EXEMPTIONS: { code: FoiaExemption; label: string }[] = [
  { code: '(b)(1)', label: '(b)(1) — Classified national defense / foreign policy' },
  { code: '(b)(2)', label: '(b)(2) — Internal personnel rules and practices' },
  { code: '(b)(3)', label: '(b)(3) — Prohibited by other statute' },
  { code: '(b)(4)', label: '(b)(4) — Trade secrets / confidential commercial' },
  { code: '(b)(5)', label: '(b)(5) — Privileged inter/intra-agency (deliberative)' },
  { code: '(b)(6)', label: '(b)(6) — Personal privacy' },
  { code: '(b)(7)', label: '(b)(7) — Law-enforcement records' },
  { code: '(b)(8)', label: '(b)(8) — Financial-institution supervision' },
  { code: '(b)(9)', label: '(b)(9) — Geological / well data' },
];
