"""
Tests for the lexical-fallback clause retrieval path (non-debt).

Covers the Codex-review fixes on /rag/clause-search:
  - infra failure raises RetrievalUnavailableError; endpoint returns 503
    with no synthesis (broken retrieval is not "no responsive precedent")
  - confidence bar: sub-MIN_SCORE hits dropped; below MIN_HITS the endpoint
    returns needs_review and never invokes the model
  - synthesis prompt is grounded in the retrieved excerpts
  - Atlas hybrid path requires explicit ATLAS_HYBRID_ENABLED — import
    availability alone must not bypass the working lexical fallback
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import atlas_retriever
from app import main as app_main

client = TestClient(app_main.app)


def _hit(clause_id: str = "5usc552-b-exemptions", score: float = 2.0,
         text: str = "Exemption text.") -> dict:
    return {
        "clause_id": clause_id,
        "title": "FOIA Exemptions",
        "score": score,
        "far_part": "5 USC 552",
        "cite": "5 U.S.C. 552(b)",
        "source_file": "5usc552-b-exemptions.md",
        "text": text,
    }


def test_clause_search_drops_hits_below_min_score(monkeypatch):
    monkeypatch.setattr(atlas_retriever, "ATLAS_HYBRID_ENABLED", False)
    monkeypatch.setattr(atlas_retriever, "MIN_SCORE", 1.0)
    monkeypatch.setattr(
        atlas_retriever, "_pymongo_text_search",
        lambda query, top_k: [_hit(score=2.0), _hit(clause_id="weak", score=0.1)],
    )
    hits = atlas_retriever.clause_search("exemption", top_k=5)
    assert [h["clause_id"] for h in hits] == ["5usc552-b-exemptions"]


def test_import_availability_alone_does_not_route_to_hybrid_stub(monkeypatch):
    # The moment langchain-mongodb is installed, the import flag flips True —
    # that must NOT bypass the working lexical path while the hybrid path is
    # an unwired stub returning [].
    monkeypatch.setattr(atlas_retriever, "_LANGCHAIN_MONGODB_AVAILABLE", True)
    monkeypatch.setattr(atlas_retriever, "ATLAS_HYBRID_ENABLED", False)
    monkeypatch.setattr(atlas_retriever, "_pymongo_text_search",
                        lambda query, top_k: [_hit()])

    def _must_not_be_reached(query, top_k):
        raise AssertionError(
            "hybrid stub reached without ATLAS_HYBRID_ENABLED")

    monkeypatch.setattr(atlas_retriever, "_atlas_hybrid_search",
                        _must_not_be_reached)
    hits = atlas_retriever.clause_search("exemption")
    assert hits == [_hit()]


def test_hybrid_path_used_only_when_explicitly_enabled(monkeypatch):
    monkeypatch.setattr(atlas_retriever, "_LANGCHAIN_MONGODB_AVAILABLE", True)
    monkeypatch.setattr(atlas_retriever, "ATLAS_HYBRID_ENABLED", True)
    monkeypatch.setattr(atlas_retriever, "_atlas_hybrid_search",
                        lambda query, top_k: [_hit(clause_id="hybrid")])
    hits = atlas_retriever.clause_search("exemption")
    assert hits[0]["clause_id"] == "hybrid"


def test_infra_failure_raises_retrieval_unavailable(monkeypatch):
    monkeypatch.setattr(atlas_retriever, "ATLAS_HYBRID_ENABLED", False)

    def _broken():
        raise atlas_retriever.RetrievalUnavailableError(
            "MongoDB connection failed")

    monkeypatch.setattr(atlas_retriever, "_get_collection", _broken)
    with pytest.raises(atlas_retriever.RetrievalUnavailableError):
        atlas_retriever.clause_search("exemption")


def test_endpoint_returns_503_on_retrieval_failure(monkeypatch):
    def _broken(query, top_k=5):
        raise atlas_retriever.RetrievalUnavailableError(
            "MongoDB connection failed")

    monkeypatch.setattr(atlas_retriever, "clause_search", _broken)
    invoked = []
    monkeypatch.setattr(app_main, "invoke_model",
                        lambda *a, **k: invoked.append(a) or {"body": "x"})
    resp = client.post("/rag/clause-search", json={"query": "exemption 5"})
    assert resp.status_code == 503
    assert "synthesis" not in resp.json()
    assert invoked == []  # never synthesize off broken retrieval


def test_endpoint_escalates_below_confidence_bar(monkeypatch):
    monkeypatch.setattr(atlas_retriever, "clause_search",
                        lambda query, top_k=5: [])
    invoked = []
    monkeypatch.setattr(app_main, "invoke_model",
                        lambda *a, **k: invoked.append(a) or {"body": "x"})
    resp = client.post("/rag/clause-search", json={"query": "exemption 5"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["needs_review"] is True
    assert body["synthesis"] is None
    assert invoked == []  # no synthesis off sub-threshold retrieval


def test_endpoint_synthesis_grounded_in_retrieved_excerpts(monkeypatch):
    hit = _hit(text="Records compiled for law enforcement purposes.")
    monkeypatch.setattr(atlas_retriever, "clause_search",
                        lambda query, top_k=5: [hit])
    prompts = []

    def _fake_invoke(prompt, **kwargs):
        prompts.append(prompt)
        return {"body": "[5usc552-b-exemptions] summary"}

    monkeypatch.setattr(app_main, "invoke_model", _fake_invoke)
    resp = client.post("/rag/clause-search",
                       json={"query": "law enforcement records"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["needs_review"] is False
    assert len(prompts) == 1
    # The model must see the retrieved source text + citation handles.
    assert hit["text"] in prompts[0]
    assert hit["clause_id"] in prompts[0]
    assert hit["cite"] in prompts[0]
