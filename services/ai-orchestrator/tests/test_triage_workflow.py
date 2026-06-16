"""
Agentic FOIA triage workflow (ADR 0005) — behavior tests.

Runs offline: no AWS creds (Bedrock stub) and no Mongo (in-memory checkpointer
+ atlas_retriever degrades to needs_review). Exercises the three HITL gates,
the pause/resume contract, and the Gate-2 scope-correction loop-back.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


def _start(client, request_id="foia-2026-test-1"):
    return client.post("/agent/intake-triage", json={
        "proposal_id": request_id,
        "raw_text": "All emails between OLP staff and outside counsel re: "
                    "surveillance guidance, Jan-Mar 2026.",
        "requester_name": "J. Reporter",
        "requester_contact": "reporter@example.org",
        "agency_id": "DOJ-OIP",
    }).json()


def test_start_pauses_at_gate_1():
    client = TestClient(app)
    res = _start(client, "foia-gate1")
    assert res["status"] == "awaiting_review"
    assert res["gate"] == "gate-1-proposed-exemptions"
    assert res["review_package"]["gate"] == "gate-1-proposed-exemptions"
    # Gate 1 must surface grounding/confidence to the reviewer (ADR 0005 §3).
    assert "needs_review" in res["review_package"]


def test_full_path_to_human_disposition():
    client = TestClient(app)
    rid = "foia-fullpath"
    assert _start(client, rid)["gate"] == "gate-1-proposed-exemptions"

    g2 = client.post("/agent/intake-triage/resume", json={
        "request_id": rid, "action": "approved"}).json()
    assert g2["status"] == "awaiting_review"
    assert g2["gate"] == "gate-2-precedent-scope"

    g3 = client.post("/agent/intake-triage/resume", json={
        "request_id": rid, "action": "approved"}).json()
    assert g3["status"] == "awaiting_review"
    assert g3["gate"] == "gate-3-final-disposition"

    # Human decides the final, requester-facing disposition (REQ-AGT-2).
    final = client.post("/agent/intake-triage/resume", json={
        "request_id": rid, "action": "approved",
        "final_outcome": "partial-release-with-redactions"}).json()
    assert final["status"] == "complete"
    assert final["final_outcome"] == "partial-release-with-redactions"
    # Append-only audit trail spans every stage + gate (REQ-AGT-4).
    stages = {a["stage"] for a in final["audit_log"]}
    assert {"intake", "classify", "route", "analyze", "recommend",
            "gate_1", "gate_2", "gate_3"} <= stages


def test_gate_3_escalates_when_undergrounded_and_no_outcome():
    client = TestClient(app)
    rid = "foia-escalate"
    _start(client, rid)
    client.post("/agent/intake-triage/resume", json={"request_id": rid, "action": "approved"})
    client.post("/agent/intake-triage/resume", json={"request_id": rid, "action": "approved"})
    # No final_outcome + under-grounded (no Mongo) -> escalate, not silent continue.
    final = client.post("/agent/intake-triage/resume", json={
        "request_id": rid, "action": "escalated"}).json()
    assert final["status"] == "escalated"
    assert final["final_outcome"] is None


def test_gate_2_scope_correction_loops_back():
    client = TestClient(app)
    rid = "foia-loopback"
    _start(client, rid)
    client.post("/agent/intake-triage/resume", json={"request_id": rid, "action": "approved"})
    # Correct scope at Gate 2 -> re-runs retrieval + analysis -> back to Gate 1.
    looped = client.post("/agent/intake-triage/resume", json={
        "request_id": rid, "action": "scope-corrected",
        "corrected_keywords": ["surveillance", "guidance"]}).json()
    assert looped["status"] == "awaiting_review"
    assert looped["gate"] == "gate-1-proposed-exemptions"
