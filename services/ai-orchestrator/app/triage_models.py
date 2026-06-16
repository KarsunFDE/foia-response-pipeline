"""
triage_models.py — typed inter-stage state for the agentic FOIA triage
workflow (ADR 0005 §4).

Every payload passed between workflow stages is a Pydantic v2 model so the
workflow is testable stage-by-stage and the audit log serializes against a
stable schema (ADR 0005 "Consequences"). Legacy keys (`proposal_id`,
`far_part`, `clause_id`) keep their FOIA-domain meaning per domain-mapping.md
and are NOT renamed.
"""
from __future__ import annotations

import operator
from enum import Enum
from typing import Annotated, Any

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- #
# Enums                                                                        #
# --------------------------------------------------------------------------- #
class ClarificationStatus(str, Enum):
    NEEDS_CLARIFICATION = "needs-clarification"
    CLEAR = "clear"


class ExemptionCode(str, Enum):
    """FOIA exemptions, 5 USC 552(b)(1)-(b)(9)."""
    B1 = "(b)(1)"
    B2 = "(b)(2)"
    B3 = "(b)(3)"
    B4 = "(b)(4)"
    B5 = "(b)(5)"
    B6 = "(b)(6)"
    B7 = "(b)(7)"
    B8 = "(b)(8)"
    B9 = "(b)(9)"


class RecommendationOutcome(str, Enum):
    """The disposition outcomes the system may RECOMMEND (hitl-plan.md
    §Recommendation Outcomes). The system never *executes* a release/withhold;
    a human decides at Gate 3 (REQ-AGT-2)."""
    FULL_RELEASE = "full-release"
    PARTIAL_RELEASE = "partial-release-with-redactions"
    FULL_WITHHOLDING = "full-withholding"
    NO_RESPONSIVE_RECORDS = "no-responsive-records"
    GLOMAR = "glomar"
    REFERRAL_CONSULTATION = "referral-or-consultation"
    CLARIFICATION_NARROWING = "clarification-or-narrowing"
    ADMINISTRATIVE_CLOSURE = "administrative-closure"


class GateName(str, Enum):
    GATE_1_EXEMPTIONS = "gate-1-proposed-exemptions"
    GATE_2_PRECEDENT = "gate-2-precedent-scope"
    GATE_3_DISPOSITION = "gate-3-final-disposition"


class ReviewAction(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    SCOPE_CORRECTED = "scope-corrected"
    ESCALATED = "escalated"


# --------------------------------------------------------------------------- #
# Leaf models                                                                  #
# --------------------------------------------------------------------------- #
class RequesterInfo(BaseModel):
    """Requester identity + contact. ⚠ Inverted FOIA threat model — the
    requester is external and potentially adversarial (PRD §threat model)."""
    name: str | None = None
    contact: str | None = None
    is_external: bool = True


class DateRange(BaseModel):
    start: str | None = None  # ISO date; scoped record date range
    end: str | None = None


class Attachment(BaseModel):
    filename: str
    content_type: str | None = None
    size_bytes: int | None = None


class Citation(BaseModel):
    """Cited federal authority or prior decision. Mirrors an atlas_retriever
    hit so retrieved sources serialize straight into the audit trail."""
    clause_id: str          # structured-output handle (domain-mapping.md)
    cite: str | None = None  # e.g. "5 USC 552(b)(5)"
    far_part: str | None = None  # legacy key; carries FOIA cite prefix
    title: str | None = None
    source_file: str | None = None
    text_snippet: str | None = None
    score: float | None = None

    @classmethod
    def from_hit(cls, hit: dict[str, Any]) -> "Citation":
        return cls(
            clause_id=hit.get("clause_id", "unknown"),
            cite=hit.get("cite"),
            far_part=hit.get("far_part"),
            title=hit.get("title"),
            source_file=hit.get("source_file"),
            text_snippet=hit.get("text"),
            score=hit.get("score"),
        )


class ProposedExemption(BaseModel):
    """A likely-exempt category proposed at the analysis stage. Any withholding
    recommendation MUST carry cited basis + foreseeable-harm + segregability
    (hitl-plan.md §Recommendation Outcomes)."""
    exemption_code: ExemptionCode
    rationale: str
    foreseeable_harm: str | None = None
    segregability: str | None = None
    citations: list[Citation] = Field(default_factory=list)
    confidence: str | None = None  # qualitative; see needs_review for the gate


class PrecedentDecision(BaseModel):
    decision_id: str
    summary: str
    outcome: RecommendationOutcome | None = None
    citations: list[Citation] = Field(default_factory=list)


class DispositionRecommendation(BaseModel):
    """AI-drafted recommendation for Gate 3. NOT a final decision — a human
    decides (REQ-AGT-2, prompt-shape rule 3)."""
    outcome: RecommendationOutcome
    rationale: str
    proposed_exemptions: list[ProposedExemption] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    segregability_analysis: str | None = None
    confidence: str | None = None


class AuditEntry(BaseModel):
    """One append-only audit row (hitl-plan.md §Audit Logging). Records prompt
    version, sources, action, and timestamp so OIP/OIG can reconstruct the run
    from the trail alone (REQ-AGT-4)."""
    stage: str
    prompt_version: str | None = None
    action: str
    detail: str | None = None
    sources: list[str] = Field(default_factory=list)
    timestamp: str  # ISO-8601 UTC; stamped by the caller (not in-graph)


class GateDecision(BaseModel):
    """A human reviewer's decision injected to resume a paused gate."""
    action: ReviewAction
    note: str | None = None
    # Gate 2 may correct scope (re-runs retrieval on the approved snapshot):
    corrected_keywords: list[str] | None = None
    corrected_date_range: DateRange | None = None
    # Gate 3 final disposition chosen by the human:
    final_outcome: RecommendationOutcome | None = None


# --------------------------------------------------------------------------- #
# Workflow state                                                               #
# --------------------------------------------------------------------------- #
class FoiaTriageState(BaseModel):
    """Workflow-scoped state carried across every stage and gate loop-back
    (ADR 0005 §4, §7). `audit_log` uses an additive reducer so each node
    appends rather than overwrites."""
    # — identity / input —
    request_id: str                       # FOIA request id (carries on proposal_id)
    foia_request: str = ""                # raw request text
    requester_info: RequesterInfo = Field(default_factory=RequesterInfo)
    agency_id: str | None = None          # tenant scope for retrieval (fail-closed)

    # — intake / classify / route (AI) —
    request_type: str | None = None
    priority: str | None = None
    target_agency: str | None = None
    date_range: DateRange | None = None
    keywords: list[str] = Field(default_factory=list)
    content_info: dict[str, Any] = Field(default_factory=dict)
    missing_fields: list[str] = Field(default_factory=list)
    clarification_status: ClarificationStatus = ClarificationStatus.CLEAR

    # — retrieval + analysis —
    citations: list[Citation] = Field(default_factory=list)
    proposed_exemptions: list[ProposedExemption] = Field(default_factory=list)
    precedent: list[PrecedentDecision] = Field(default_factory=list)

    # — recommendation / disposition —
    recommendation: DispositionRecommendation | None = None
    final_outcome: RecommendationOutcome | None = None

    # — control / gating —
    needs_review: bool = False            # set by retrieval gating (ADR 0004)
    review_reason: str | None = None
    escalated: bool = False               # Gate 3 escalation (under-grounded)
    prompt_versions: dict[str, str] = Field(default_factory=dict)
    gate_decisions: dict[str, GateDecision] = Field(default_factory=dict)

    # — audit (append-only; additive reducer) —
    audit_log: Annotated[list[AuditEntry], operator.add] = Field(default_factory=list)
