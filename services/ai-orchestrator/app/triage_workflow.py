"""
triage_workflow.py — agentic FOIA triage workflow (ADR 0005).

LangGraph StateGraph with the ADR 0005 stage pipeline:

    intake → classify → route            (AI — assist, human disposes)
      → retrieve_authority → score_filter (TOOL — deterministic, auditable)
      → analyze                           (AI)
      → [GATE 1] review proposed exemptions
      → retrieve_precedent                (TOOL)
      → [GATE 2] review precedent; scope-correct loops back to retrieve_authority
      → recommend                         (AI)
      → [GATE 3] final disposition (RISKY) — human decides; under-grounded → escalate

Load-bearing controls (ADR 0005 §2-3):
  - The LLM NEVER retrieves, ranks, or thresholds. Retrieval + the score/top-k
    cut + precedent pull are deterministic tool calls (atlas_retriever) so the
    audit trail records reproducible I/O, not LLM prose.
  - All three gates are `interrupt()` pauses requiring human approval. A
    MongoDB checkpointer persists state by request_id (thread_id) so a paused
    decision survives a restart and resumes without regeneration (REQ-AGT-3).
  - The "withhold/escalate confidence bar" reuses the existing atlas_retriever
    gating (ADR 0004): lexical path → always needs_review; below MIN_HITS →
    escalate. No new threshold invented.
  - Every AI node uses Claude Sonnet via ChatBedrockConverse (ADR 0005 §5) with
    an assisting-role system prompt that states the AI does not decide
    (ADR 0005 §6). Falls back to a deterministic stub when AWS creds don't
    resolve, so the stack still flows offline.
"""
from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timezone
from typing import Any

from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt, Command

from app import atlas_retriever
from app.bedrock_client import BEDROCK_MODEL_ID, AWS_REGION
from app.triage_models import (
    AuditEntry,
    Citation,
    ClarificationStatus,
    DateRange,
    DispositionRecommendation,
    ExemptionCode,
    FoiaTriageState,
    GateDecision,
    GateName,
    PrecedentDecision,
    ProposedExemption,
    RecommendationOutcome,
    ReviewAction,
)

log = logging.getLogger("ai-orchestrator.triage")

# Pinned per-phase prompt versions. Gate 2 loop-back re-runs on the pinned
# version so retrieval/prompt drift between attempts is impossible (ADR 0005 §3).
PROMPT_VERSIONS = {
    "intake": "intake-v1",
    "classify": "classify-v1",
    "route": "route-v1",
    "analyze": "analyze-v1",
    "recommend": "recommend-v1",
}

# Assisting-role system prompts (hitl-plan.md §Example System Prompts). Each
# states the AI does NOT make the final decision (ADR 0005 §6).
SYS_INTAKE = (
    "You are assisting with FOIA intake triage. Summarize the request, identify "
    "the likely request type, and flag urgency or ambiguity and any missing "
    "required fields. Do not make a final release decision."
)
SYS_CLASSIFY = (
    "You are assisting with FOIA classification. Identify the likely request "
    "type and likely-exempt categories (5 USC 552(b)(1)-(b)(9)). You assist; a "
    "human reviewer decides. Do not make a final release decision."
)
SYS_ROUTE = (
    "You are assisting with FOIA routing. Recommend the target agency/component "
    "and a priority. Routing is reversible and not a release decision."
)
SYS_ANALYZE = (
    "You are assisting with FOIA exemption analysis. Review the request and the "
    "retrieved legal/precedent material. Suggest applicable exemptions ONLY when "
    "supported by the cited authority below. If support is weak or unclear, say "
    "so explicitly. You do not make the final decision."
)
SYS_RECOMMEND = (
    "You are assisting a FOIA officer. Draft a recommendation for release or "
    "withholding based ONLY on the analyzed request, cited exemptions, and "
    "retrieved precedent. Provide a concise justification. Do not present the "
    "result as final — a human reviewer makes the final decision."
)

_EXEMPTION_RE = re.compile(r"\(b\)\((\d)\)")


# --------------------------------------------------------------------------- #
# Bedrock chat model (v1.0 idiom) with offline stub fallback                   #
# --------------------------------------------------------------------------- #
_model: Any = None
_model_init_failed = False


def _get_chat_model() -> Any:
    global _model, _model_init_failed
    if _model is None and not _model_init_failed:
        try:
            from langchain_aws import ChatBedrockConverse

            _model = ChatBedrockConverse(
                model_id=BEDROCK_MODEL_ID,
                region_name=AWS_REGION,
                temperature=0.2,
                max_tokens=1024,
            )
        except Exception as exc:  # pragma: no cover - import/cred edge
            log.warning("ChatBedrockConverse init failed (%s); using stub", exc)
            _model_init_failed = True
    return _model


def _chat(prompt: str, system: str) -> str:
    """Invoke Claude Sonnet via Bedrock; deterministic stub when creds absent."""
    model = _get_chat_model()
    if model is None:
        return _offline_stub(prompt, system)
    try:
        from langchain_core.messages import HumanMessage, SystemMessage

        resp = model.invoke([SystemMessage(content=system), HumanMessage(content=prompt)])
        content = resp.content
        return content if isinstance(content, str) else str(content)
    except Exception as exc:  # pragma: no cover - network/cred edge
        log.warning("bedrock chat failed (%s); returning stub", exc)
        return _offline_stub(prompt, system)


def _offline_stub(prompt: str, system: str) -> str:
    """Deterministic offline response used when AWS creds don't resolve.

    GROUNDED, not invented: for the analysis step it echoes back ONLY the
    (b)(N) exemption codes that already appear in the retrieved authority
    passed in the prompt, so the analyze node proposes nothing the corpus did
    not surface. Marked ``[offline-stub]`` so it is never mistaken for live
    Bedrock output. With no retrieved authority (e.g. Mongo absent in tests)
    no codes are present, so the fallback degrades to the prior plain stub
    and the offline test contract is unchanged.
    """
    if "exemption" in system.lower():
        # Prefer codes named in an authority TITLE/heading line (e.g.
        # "Exemption (b)(5) — Deliberative-process privilege") — far more
        # targeted than the all-nine enumeration chunk body. Fall back to the
        # first few codes seen anywhere, capped so we never "propose" all nine.
        title_codes = sorted({
            f"(b)({n})"
            for line in prompt.splitlines() if "exemption (b)" in line.lower()
            for n in _EXEMPTION_RE.findall(line)
        })
        codes = title_codes or sorted({f"(b)({n})" for n in _EXEMPTION_RE.findall(prompt)})[:3]
        if codes:
            lines = [
                f"{c} — supported by the cited authority retrieved above; "
                f"a human reviewer confirms applicability and segregability."
                for c in codes
            ]
            return "[offline-stub] Likely applicable exemptions:\n" + "\n".join(lines)
    return f"[offline-stub] {system.split('.')[0]} :: {prompt[:120]}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _audit(stage: str, action: str, *, prompt_version: str | None = None,
           detail: str | None = None, sources: list[str] | None = None) -> AuditEntry:
    return AuditEntry(
        stage=stage,
        prompt_version=prompt_version,
        action=action,
        detail=detail,
        sources=sources or [],
        timestamp=_now(),
    )


# --------------------------------------------------------------------------- #
# AI nodes (intake / classify / route)                                         #
# --------------------------------------------------------------------------- #
def intake_node(state: FoiaTriageState) -> dict[str, Any]:
    body = _chat(
        f"FOIA request:\n{state.foia_request}\n\nSummarize it and list any "
        f"missing required fields (requester identity, contact, records sought, "
        f"date range).",
        SYS_INTAKE,
    )
    missing: list[str] = []
    if not state.requester_info.name:
        missing.append("requester_name")
    if not state.requester_info.contact:
        missing.append("requester_contact")
    if not state.foia_request.strip():
        missing.append("records_sought")
    status = (ClarificationStatus.NEEDS_CLARIFICATION if missing
              else ClarificationStatus.CLEAR)
    return {
        "missing_fields": missing,
        "clarification_status": status,
        "content_info": {"intake_summary": body},
        "prompt_versions": {**state.prompt_versions, "intake": PROMPT_VERSIONS["intake"]},
        "audit_log": [_audit("intake", "summarized",
                             prompt_version=PROMPT_VERSIONS["intake"],
                             detail=f"missing={missing}")],
    }


def classify_node(state: FoiaTriageState) -> dict[str, Any]:
    body = _chat(
        f"FOIA request:\n{state.foia_request}\n\nState the likely request type "
        f"and any likely-exempt categories as (b)(N) codes with one-line reasons.",
        SYS_CLASSIFY,
    )
    # Derive scoping keywords deterministically (tool-side input, not an LLM cut).
    words = re.findall(r"[A-Za-z]{4,}", state.foia_request.lower())
    keywords = sorted({w for w in words if w not in _STOPWORDS})[:8]
    return {
        "request_type": (body.splitlines()[0][:120] if body else None),
        "keywords": keywords,
        "content_info": {**state.content_info, "classification": body},
        "prompt_versions": {**state.prompt_versions, "classify": PROMPT_VERSIONS["classify"]},
        "audit_log": [_audit("classify", "classified",
                             prompt_version=PROMPT_VERSIONS["classify"],
                             detail=f"keywords={keywords}")],
    }


def route_node(state: FoiaTriageState) -> dict[str, Any]:
    body = _chat(
        f"FOIA request:\n{state.foia_request}\n\nRecommend a target "
        f"agency/component and a priority (routine/expedited).",
        SYS_ROUTE,
    )
    priority = "expedited" if "expedit" in body.lower() else "routine"
    target = state.target_agency or state.agency_id
    return {
        "target_agency": target,
        "priority": priority,
        "content_info": {**state.content_info, "routing": body},
        "prompt_versions": {**state.prompt_versions, "route": PROMPT_VERSIONS["route"]},
        "audit_log": [_audit("route", "routed",
                             prompt_version=PROMPT_VERSIONS["route"],
                             detail=f"target={target} priority={priority}")],
    }


# --------------------------------------------------------------------------- #
# TOOL nodes (deterministic — atlas_retriever). LLM never runs here.           #
# --------------------------------------------------------------------------- #
def _retrieval_query(state: FoiaTriageState) -> str:
    return " ".join([state.foia_request, *state.keywords]).strip() or state.foia_request


def retrieve_authority_node(state: FoiaTriageState) -> dict[str, Any]:
    query = _retrieval_query(state)
    try:
        hits = atlas_retriever.clause_search(
            query, top_k=5, far_part=None, agency_id=state.agency_id
        )
    except atlas_retriever.RetrievalUnavailableError as exc:
        # Infra failure is NOT "no responsive precedent" — degrade + flag for
        # escalation; never synthesize off broken retrieval.
        return {
            "needs_review": True,
            "review_reason": f"authority retrieval unavailable: {exc}",
            "audit_log": [_audit("retrieve_authority", "retrieval_unavailable",
                                 detail=str(exc))],
        }
    citations = [Citation.from_hit(h) for h in hits]
    return {
        "citations": citations,
        "audit_log": [_audit("retrieve_authority", "retrieved",
                             detail=f"hits={len(hits)} agency={state.agency_id}",
                             sources=[c.clause_id for c in citations])],
    }


def score_filter_node(state: FoiaTriageState) -> dict[str, Any]:
    """Deterministic confidence gate, reusing atlas_retriever semantics
    (ADR 0004): below MIN_HITS → escalate; lexical path → always needs_review."""
    hits = state.citations
    if len(hits) < atlas_retriever.MIN_HITS:
        return {
            "needs_review": True,
            "review_reason": ("no hits at or above the retrieval confidence bar; "
                              "escalate to a human reviewer (withhold-by-default)"),
            "audit_log": [_audit("score_filter", "below_min_hits",
                                 detail=f"hits={len(hits)} min={atlas_retriever.MIN_HITS}")],
        }
    lexical = atlas_retriever.lexical_path_active()
    reason = (None if not lexical else
              "lexical-fallback retrieval scores are uncalibrated (Mongo $text is "
              "not normalized confidence); a human reviewer must validate.")
    return {
        "needs_review": lexical or state.needs_review,
        "review_reason": reason or state.review_reason,
        "audit_log": [_audit("score_filter", "passed",
                             detail=f"hits={len(hits)} lexical_path={lexical}")],
    }


def retrieve_precedent_node(state: FoiaTriageState) -> dict[str, Any]:
    query = _retrieval_query(state) + " prior decision precedent"
    try:
        hits = atlas_retriever.clause_search(
            query, top_k=3, far_part=None, agency_id=state.agency_id
        )
    except atlas_retriever.RetrievalUnavailableError as exc:
        return {
            "needs_review": True,
            "review_reason": f"precedent retrieval unavailable: {exc}",
            "audit_log": [_audit("retrieve_precedent", "retrieval_unavailable",
                                 detail=str(exc))],
        }
    precedent = [
        PrecedentDecision(
            decision_id=h.get("clause_id", "unknown"),
            summary=(h.get("text") or "")[:300],
            citations=[Citation.from_hit(h)],
        )
        for h in hits
    ]
    return {
        "precedent": precedent,
        "audit_log": [_audit("retrieve_precedent", "retrieved",
                             detail=f"precedent={len(precedent)}",
                             sources=[p.decision_id for p in precedent])],
    }


# --------------------------------------------------------------------------- #
# AI node (analyze) + recommendation                                           #
# --------------------------------------------------------------------------- #
def analyze_node(state: FoiaTriageState) -> dict[str, Any]:
    excerpts = "\n\n".join(
        f"[{c.clause_id}] {c.cite or c.far_part or ''} — {c.title or ''}\n"
        f"{c.text_snippet or ''}"
        for c in state.citations
    ) or "(no retrieved authority)"
    body = _chat(
        f"FOIA request:\n{state.foia_request}\n\nRetrieved authority:\n{excerpts}\n\n"
        f"List likely applicable exemptions as (b)(N) with a one-line rationale "
        f"each, citing the bracketed clause_id. If support is weak, say so.",
        SYS_ANALYZE,
    )
    # Map detected (b)(N) codes to ProposedExemption, grounded in retrieved cites.
    found = {f"(b)({n})" for n in _EXEMPTION_RE.findall(body)}
    exemptions: list[ProposedExemption] = []
    for code_str in sorted(found):
        try:
            code = ExemptionCode(code_str)
        except ValueError:
            continue
        exemptions.append(ProposedExemption(
            exemption_code=code,
            rationale=f"proposed from analysis; see cited authority ({code_str})",
            citations=list(state.citations),
            confidence=("low" if state.needs_review else "moderate"),
        ))
    return {
        "proposed_exemptions": exemptions,
        "content_info": {**state.content_info, "analysis": body},
        "prompt_versions": {**state.prompt_versions, "analyze": PROMPT_VERSIONS["analyze"]},
        "audit_log": [_audit("analyze", "analyzed",
                             prompt_version=PROMPT_VERSIONS["analyze"],
                             detail=f"exemptions={[e.exemption_code.value for e in exemptions]}",
                             sources=[c.clause_id for c in state.citations])],
    }


def recommend_node(state: FoiaTriageState) -> dict[str, Any]:
    exemption_summary = ", ".join(e.exemption_code.value for e in state.proposed_exemptions) or "none"
    body = _chat(
        f"FOIA request:\n{state.foia_request}\n\nProposed exemptions: "
        f"{exemption_summary}\nPrecedent decisions: {len(state.precedent)}\n\n"
        f"Draft a disposition recommendation (full release / partial release with "
        f"redactions / full withholding / no responsive records / Glomar / "
        f"referral / clarification / administrative closure), a concise rationale, "
        f"and a segregability note if withholding. Do not present as final.",
        SYS_RECOMMEND,
    )
    # Conservative default: any proposed exemption → partial release with
    # redactions; none → full release. The human decides at Gate 3 regardless.
    outcome = (RecommendationOutcome.PARTIAL_RELEASE if state.proposed_exemptions
               else RecommendationOutcome.FULL_RELEASE)
    rec = DispositionRecommendation(
        outcome=outcome,
        rationale=body,
        proposed_exemptions=list(state.proposed_exemptions),
        citations=list(state.citations),
        segregability_analysis=("segregable portions to be released; withheld "
                                "portions limited to cited exemptions"
                                if state.proposed_exemptions else None),
        confidence=("low" if state.needs_review else "moderate"),
    )
    return {
        "recommendation": rec,
        "prompt_versions": {**state.prompt_versions, "recommend": PROMPT_VERSIONS["recommend"]},
        "audit_log": [_audit("recommend", "drafted",
                             prompt_version=PROMPT_VERSIONS["recommend"],
                             detail=f"outcome={outcome.value} needs_review={state.needs_review}")],
    }


# --------------------------------------------------------------------------- #
# HITL gates (interrupt). Code before interrupt() must be side-effect-free —   #
# LangGraph replays the node from the top on resume.                           #
# --------------------------------------------------------------------------- #
def gate1_node(state: FoiaTriageState) -> dict[str, Any]:
    decision_raw = interrupt({
        "gate": GateName.GATE_1_EXEMPTIONS.value,
        "summary": "Review proposed exemptions before they propagate.",
        "proposed_exemptions": [e.model_dump() for e in state.proposed_exemptions],
        "citations": [c.model_dump() for c in state.citations],
        "needs_review": state.needs_review,
        "review_reason": state.review_reason,
    })
    decision = _as_decision(decision_raw)
    return {
        "gate_decisions": {**state.gate_decisions, GateName.GATE_1_EXEMPTIONS.value: decision},
        "audit_log": [_audit("gate_1", decision.action.value, detail=decision.note)],
    }


def gate2_node(state: FoiaTriageState) -> dict[str, Any]:
    decision_raw = interrupt({
        "gate": GateName.GATE_2_PRECEDENT.value,
        "summary": "Review precedent scope. Correct/reject to loop back through "
                   "retrieval + analysis on the approved snapshot.",
        "precedent": [p.model_dump() for p in state.precedent],
        "keywords": state.keywords,
        "date_range": state.date_range.model_dump() if state.date_range else None,
    })
    decision = _as_decision(decision_raw)
    updates: dict[str, Any] = {
        "gate_decisions": {**state.gate_decisions, GateName.GATE_2_PRECEDENT.value: decision},
        "audit_log": [_audit("gate_2", decision.action.value, detail=decision.note)],
    }
    # Scope correction: apply the approved snapshot, loop edge re-runs retrieval.
    if decision.action in (ReviewAction.SCOPE_CORRECTED, ReviewAction.REJECTED):
        if decision.corrected_keywords is not None:
            updates["keywords"] = decision.corrected_keywords
        if decision.corrected_date_range is not None:
            updates["date_range"] = decision.corrected_date_range
    return updates


def gate3_node(state: FoiaTriageState) -> dict[str, Any]:
    decision_raw = interrupt({
        "gate": GateName.GATE_3_DISPOSITION.value,
        "summary": "RISKY — final, requester-facing disposition. The system "
                   "never auto-releases or auto-withholds; you decide.",
        "recommendation": state.recommendation.model_dump() if state.recommendation else None,
        "needs_review": state.needs_review,
        "review_reason": state.review_reason,
    })
    decision = _as_decision(decision_raw)
    # Under-grounded → escalate, do not silently continue (ADR 0005 §3).
    escalate = decision.action == ReviewAction.ESCALATED or (
        state.needs_review and decision.final_outcome is None
    )
    return {
        "gate_decisions": {**state.gate_decisions, GateName.GATE_3_DISPOSITION.value: decision},
        "final_outcome": (None if escalate else
                          (decision.final_outcome
                           or (state.recommendation.outcome if state.recommendation else None))),
        "escalated": escalate,
        "audit_log": [_audit("gate_3", decision.action.value,
                             detail=f"escalated={escalate} "
                                    f"final={decision.final_outcome.value if decision.final_outcome else None}")],
    }


def _as_decision(raw: Any) -> GateDecision:
    if isinstance(raw, GateDecision):
        return raw
    if isinstance(raw, dict):
        return GateDecision(**raw)
    # Bare truthy/string resume → approve.
    return GateDecision(action=ReviewAction.APPROVED, note=str(raw) if raw else None)


def _route_after_gate2(state: FoiaTriageState) -> str:
    decision = state.gate_decisions.get(GateName.GATE_2_PRECEDENT.value)
    if decision and decision.action in (ReviewAction.SCOPE_CORRECTED, ReviewAction.REJECTED):
        return "retrieve_authority"   # loop back on the approved snapshot
    return "recommend"


# --------------------------------------------------------------------------- #
# Graph assembly + checkpointer                                                #
# --------------------------------------------------------------------------- #
_GRAPH: Any = None


def _build_checkpointer() -> Any:
    mongo_url = os.environ.get("MONGO_URL")
    if mongo_url:
        try:
            from langgraph.checkpoint.mongodb import MongoDBSaver
            from pymongo import MongoClient

            client = MongoClient(mongo_url, serverSelectionTimeoutMS=1500)
            client.admin.command("ping")
            log.info("triage checkpointer: MongoDBSaver (persists across restart)")
            return MongoDBSaver(client)
        except Exception as exc:
            log.warning("Mongo checkpointer unavailable (%s); in-memory fallback "
                        "(no restart persistence)", exc)
    from langgraph.checkpoint.memory import InMemorySaver
    return InMemorySaver()


def get_graph() -> Any:
    global _GRAPH
    if _GRAPH is None:
        b = StateGraph(FoiaTriageState)
        b.add_node("intake", intake_node)
        b.add_node("classify", classify_node)
        b.add_node("route", route_node)
        b.add_node("retrieve_authority", retrieve_authority_node)
        b.add_node("score_filter", score_filter_node)
        b.add_node("analyze", analyze_node)
        b.add_node("gate1", gate1_node)
        b.add_node("retrieve_precedent", retrieve_precedent_node)
        b.add_node("gate2", gate2_node)
        b.add_node("recommend", recommend_node)
        b.add_node("gate3", gate3_node)

        b.add_edge(START, "intake")
        b.add_edge("intake", "classify")
        b.add_edge("classify", "route")
        b.add_edge("route", "retrieve_authority")
        b.add_edge("retrieve_authority", "score_filter")
        b.add_edge("score_filter", "analyze")
        b.add_edge("analyze", "gate1")
        b.add_edge("gate1", "retrieve_precedent")
        b.add_edge("retrieve_precedent", "gate2")
        b.add_conditional_edges("gate2", _route_after_gate2,
                                {"retrieve_authority": "retrieve_authority",
                                 "recommend": "recommend"})
        b.add_edge("recommend", "gate3")
        b.add_edge("gate3", END)

        _GRAPH = b.compile(checkpointer=_build_checkpointer())
    return _GRAPH


# --------------------------------------------------------------------------- #
# Public entry points (called from main.py)                                    #
# --------------------------------------------------------------------------- #
def start_triage(state: FoiaTriageState) -> dict[str, Any]:
    config = {"configurable": {"thread_id": state.request_id}}
    result = get_graph().invoke(state, config=config)
    return _summarize(result, state.request_id)


def resume_triage(request_id: str, decision: GateDecision) -> dict[str, Any]:
    config = {"configurable": {"thread_id": request_id}}
    result = get_graph().invoke(Command(resume=decision.model_dump()), config=config)
    return _summarize(result, request_id)


def _summarize(result: dict[str, Any], request_id: str) -> dict[str, Any]:
    interrupts = result.get("__interrupt__")
    if interrupts:
        payload = interrupts[0].value if hasattr(interrupts[0], "value") else interrupts[0]
        return {
            "request_id": request_id,
            "status": "awaiting_review",
            "gate": payload.get("gate") if isinstance(payload, dict) else None,
            "review_package": payload,
            "thread_id": request_id,
        }
    rec = result.get("recommendation")
    return {
        "request_id": request_id,
        "status": "escalated" if result.get("escalated") else "complete",
        "final_outcome": (result.get("final_outcome").value
                          if hasattr(result.get("final_outcome"), "value")
                          else result.get("final_outcome")),
        "recommendation": rec.model_dump() if hasattr(rec, "model_dump") else rec,
        "needs_review": result.get("needs_review"),
        "review_reason": result.get("review_reason"),
        "audit_log": [a.model_dump() if hasattr(a, "model_dump") else a
                      for a in result.get("audit_log", [])],
        "thread_id": request_id,
    }


_STOPWORDS = {
    "this", "that", "with", "from", "have", "would", "about", "which", "their",
    "there", "between", "regarding", "request", "records", "please", "under",
    "shall", "such", "into", "your", "ours", "they", "them", "were", "been",
    "documents", "document", "information", "email", "emails",
}
