/**
 * Agentic FOIA triage workflow types (ADR 0005) — frontend mirror of the
 * ai-orchestrator triage_models.py payloads. These shape the responses from
 * POST /api/ai/agent/intake-triage[/resume] and POST /api/ai/rag/clause-search.
 *
 * Legacy key note (domain-mapping.md): the intake request carries the FOIA
 * request id on `proposal_id`; `clause_id` is the structured-output handle.
 */

export interface TriageCitation {
  clause_id: string;
  cite?: string | null;
  far_part?: string | null;
  title?: string | null;
  source_file?: string | null;
  text_snippet?: string | null;
  score?: number | null;
}

export interface ProposedExemption {
  exemption_code: string;       // "(b)(1)"–"(b)(9)"
  rationale: string;
  foreseeable_harm?: string | null;
  segregability?: string | null;
  citations: TriageCitation[];
  confidence?: string | null;
}

export interface PrecedentDecision {
  decision_id: string;
  summary: string;
  outcome?: string | null;
  citations: TriageCitation[];
}

export interface DispositionRecommendation {
  outcome: string;
  rationale: string;
  proposed_exemptions: ProposedExemption[];
  citations: TriageCitation[];
  segregability_analysis?: string | null;
  confidence?: string | null;
}

export interface AuditEntry {
  stage: string;
  prompt_version?: string | null;
  action: string;
  detail?: string | null;
  sources: string[];
  timestamp: string;
}

/** review_package — fields present depend on which gate is paused. */
export interface ReviewPackage {
  gate: string;
  summary?: string;
  // Gate 1
  proposed_exemptions?: ProposedExemption[];
  citations?: TriageCitation[];
  needs_review?: boolean;
  review_reason?: string | null;
  // Gate 2
  precedent?: PrecedentDecision[];
  keywords?: string[];
  date_range?: { start?: string | null; end?: string | null } | null;
  // Gate 3
  recommendation?: DispositionRecommendation | null;
}

export type TriageStatus = 'awaiting_review' | 'complete' | 'escalated';

export interface TriageResult {
  request_id: string;
  status: TriageStatus | string;
  gate?: string | null;
  review_package?: ReviewPackage | null;
  final_outcome?: string | null;
  recommendation?: DispositionRecommendation | null;
  needs_review?: boolean | null;
  review_reason?: string | null;
  audit_log?: AuditEntry[] | null;
  thread_id?: string | null;
}

export interface IntakeTriageRequest {
  proposal_id: string;          // carries the FOIA request id (domain-mapping.md)
  foia_request_id?: string;
  raw_text?: string;
  requester_name?: string;
  requester_contact?: string;
  agency_id?: string;
  date_range_start?: string;
  date_range_end?: string;
}

export type ReviewActionValue = 'approved' | 'rejected' | 'scope-corrected' | 'escalated';

export interface TriageResumeRequest {
  request_id: string;
  action: ReviewActionValue;
  note?: string;
  corrected_keywords?: string[];
  final_outcome?: string;
}

export interface ClauseSearchResult {
  query: string;
  hits: TriageCitation[];
  synthesis?: string | null;
  needs_review?: boolean;
  review_reason?: string | null;
  model?: string;
}

/** Disposition outcomes a human may select at Gate 3 (RecommendationOutcome). */
export const DISPOSITION_OUTCOMES: { value: string; label: string }[] = [
  { value: 'full-release', label: 'Full release' },
  { value: 'partial-release-with-redactions', label: 'Partial release with redactions' },
  { value: 'full-withholding', label: 'Full withholding' },
  { value: 'no-responsive-records', label: 'No responsive records' },
  { value: 'glomar', label: 'Glomar (neither confirm nor deny)' },
  { value: 'referral-or-consultation', label: 'Referral / consultation' },
  { value: 'clarification-or-narrowing', label: 'Clarification / narrowing' },
  { value: 'administrative-closure', label: 'Administrative closure' },
];
