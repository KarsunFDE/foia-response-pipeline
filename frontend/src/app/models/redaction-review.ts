/**
 * RedactionReview — exemption analysis + redaction proposal/review for a
 * FOIA request (5 USC 552(b), 28 CFR 16.6).
 *
 * Domain reshape from the acquire-gov Evaluation (TEP) baseline. A redaction
 * review proposes exemptions over a responsive document, records the
 * rationale, and produces a release/withhold determination that is HITL-gated
 * because release is irreversible. The General Counsel / FOIA Officer is the
 * reviewer; a denial is appealable (5 USC 552(a)(6)(A)(i)).
 *
 * NOTE on legacy types: `RedactionReviewFactor` and `RedactionReviewScore`
 * (TEP source-selection shapes) remain only so the inherited acquisition
 * components (evaluator-workspace, consensus-ssdd) still compile. They are
 * NOT part of the FOIA shape — the pair repurposes/deletes them in W4–W5.
 */
import { FoiaExemption } from './foia-request';

/** Who is performing / signing the redaction review. */
export type ReviewerRole = 'foia_officer' | 'general_counsel' | 'records_custodian';

/** HITL release determination (irreversible — gated). */
export type ReleaseDecision = 'release_full' | 'release_partial' | 'withhold';

/**
 * Redaction-review workflow state (replaces the TEP panel state machine).
 *   PROPOSED -> UNDER_REVIEW -> APPROVED_FOR_RELEASE / WITHHELD
 */
export type RedactionReviewState =
  | 'PROPOSED'
  | 'UNDER_REVIEW'
  | 'APPROVED_FOR_RELEASE'
  | 'WITHHELD';

/** A single proposed redaction tied to one or more exemptions. */
export interface ProposedRedaction {
  id: string;
  /** Page or segment reference within the document. */
  segmentRef: string;
  /** Exemptions claimed for this segment. */
  exemptions: FoiaExemption[];
  /** Why this segment is withheld (the deliberative/privacy/etc. basis). */
  rationale: string;
}

export interface RedactionReview {
  id: string;
  foiaRequestId: string;
  agencyId?: string;
  /** Reference to the responsive document under review. */
  documentRef: string;
  proposedRedactions: ProposedRedaction[];
  reviewerRole: ReviewerRole;
  state: RedactionReviewState;
  releaseDecision: ReleaseDecision | null;
  /** A denial / partial-grant is appealable by the requester. */
  appealable: boolean;
  createdAt?: string;
  decidedAt?: string | null;
}

/**
 * ⚠ LEGACY (acquisition-era TEP source-selection). Retained only so the
 * inherited acquisition components compile; not part of the FOIA shape.
 */
export interface RedactionReviewFactor {
  id: string;
  name: string;
  weight: number;
  sectionM: string;
}

export interface RedactionReviewScore {
  evaluatorId: string;
  evaluatorName: string;
  proposalId: string;
  factorId: string;
  score: number;
  narrative: string;
  submittedAt: string;
}

/**
 * ⚠ LEGACY (acquisition-era TEP panel record). Used only by the inherited
 * evaluator-workspace / consensus-ssdd components and their demo fixture.
 * Repurposed/deleted by the pair in W4–W5.
 */
export type LegacyTepReviewState =
  | 'PANEL_ASSIGNMENT'
  | 'INDIVIDUAL_SCORING'
  | 'CONSENSUS'
  | 'SSDD_DRAFT'
  | 'AWAITING_SSA_SIGNATURE'
  | 'AWARDED';

export interface LegacyTepReview {
  id: string;
  foiaRequestId: string;
  panelMembers: string[];
  factors: RedactionReviewFactor[];
  state: LegacyTepReviewState;
  ssddDocId: string | null;
}
