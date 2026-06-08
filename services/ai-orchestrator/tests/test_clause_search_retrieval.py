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
        "chunk_index": 0,
        "heading_path": ["FOIA Exemptions"],
        "text": text,
    }


def test_clause_search_drops_hits_below_min_score(monkeypatch):
    monkeypatch.setattr(atlas_retriever, "ATLAS_HYBRID_ENABLED", False)
    monkeypatch.setattr(atlas_retriever, "MIN_SCORE", 1.0)
    monkeypatch.setattr(
        atlas_retriever, "_pymongo_text_search",
        lambda query, top_k, far_part=None, agency_id=None: [
            _hit(score=2.0), _hit(clause_id="weak", score=0.1)],
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
                        lambda query, top_k, far_part=None, agency_id=None: [_hit()])

    def _must_not_be_reached(query, top_k, far_part=None, agency_id=None):
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
                        lambda query, top_k, far_part=None, agency_id=None: [
                            _hit(clause_id="hybrid")])
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
    def _broken(query, top_k=5, far_part=None, agency_id=None):
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
                        lambda query, top_k=5, far_part=None, agency_id=None: [])
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
                        lambda query, top_k=5, far_part=None, agency_id=None: [hit])
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


def test_clause_search_forwards_far_part_to_pymongo(monkeypatch):
    # far_part is an exact-match pre-filter; clause_search must thread it
    # through to the lexical search rather than dropping it.
    monkeypatch.setattr(atlas_retriever, "ATLAS_HYBRID_ENABLED", False)
    captured = {}

    def _fake_search(query, top_k, far_part=None, agency_id=None):
        captured["query"] = query
        captured["top_k"] = top_k
        captured["far_part"] = far_part
        return [_hit()]

    monkeypatch.setattr(atlas_retriever, "_pymongo_text_search", _fake_search)
    atlas_retriever.clause_search("x", far_part="5 USC 552")
    assert captured["far_part"] == "5 USC 552"


def test_endpoint_forwards_far_part_to_clause_search(monkeypatch):
    # POST body far_part must reach clause_search as a kwarg.
    captured = {}

    def _fake_clause_search(query, top_k=5, far_part=None, agency_id=None):
        captured["query"] = query
        captured["top_k"] = top_k
        captured["far_part"] = far_part
        return [_hit()]

    monkeypatch.setattr(atlas_retriever, "clause_search", _fake_clause_search)
    monkeypatch.setattr(app_main, "invoke_model",
                        lambda *a, **k: {"body": "stub synthesis"})
    resp = client.post("/rag/clause-search",
                       json={"query": "exemption", "far_part": "5 USC 552"})
    assert resp.status_code == 200
    assert captured["far_part"] == "5 USC 552"


def test_endpoint_success_response_shape(monkeypatch):
    monkeypatch.setattr(atlas_retriever, "clause_search",
                        lambda query, top_k=5, far_part=None, agency_id=None: [_hit()])
    monkeypatch.setattr(app_main, "invoke_model",
                        lambda *a, **k: {"body": "[5usc552-b-exemptions] summary"})
    resp = client.post("/rag/clause-search", json={"query": "exemption"})
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {
        "query", "hits", "synthesis", "needs_review", "model"}
    assert body["needs_review"] is False
    assert body["synthesis"] is not None


def test_endpoint_escalation_response_shape(monkeypatch):
    # Sub-confidence-bar path carries the extra review_reason key and never
    # synthesizes.
    monkeypatch.setattr(atlas_retriever, "clause_search",
                        lambda query, top_k=5, far_part=None, agency_id=None: [])
    monkeypatch.setattr(app_main, "invoke_model",
                        lambda *a, **k: {"body": "should not be called"})
    resp = client.post("/rag/clause-search", json={"query": "exemption"})
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {
        "query", "hits", "synthesis", "needs_review", "review_reason", "model"}
    assert body["needs_review"] is True
    assert body["synthesis"] is None


def test_endpoint_escalates_on_hallucinated_citation(monkeypatch):
    # Model invents a clause_id that is not in the retrieved hit set — this is
    # not traceable authority, so the synthesis must be withheld + escalated.
    monkeypatch.setattr(atlas_retriever, "clause_search",
                        lambda query, top_k=5, far_part=None, agency_id=None: [_hit()])
    monkeypatch.setattr(app_main, "invoke_model",
                        lambda *a, **k: {"body": "[hallucinated-clause] made-up text"})
    resp = client.post("/rag/clause-search", json={"query": "exemption"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["needs_review"] is True
    assert body["synthesis"] is None
    assert body["review_reason"]
    assert set(body.keys()) == {
        "query", "hits", "synthesis", "needs_review", "review_reason", "model"}


def test_endpoint_escalates_on_uncited_synthesis(monkeypatch):
    # Model emits zero bracketed citations — uncited claims are not traceable.
    monkeypatch.setattr(atlas_retriever, "clause_search",
                        lambda query, top_k=5, far_part=None, agency_id=None: [_hit()])
    monkeypatch.setattr(app_main, "invoke_model",
                        lambda *a, **k: {"body": "uncited summary text"})
    resp = client.post("/rag/clause-search", json={"query": "exemption"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["needs_review"] is True
    assert body["synthesis"] is None
    assert body["review_reason"]


def test_endpoint_accepts_when_all_citations_in_hit_set(monkeypatch):
    # Multiple hits, body cites both clause_ids — fully grounded, so the
    # synthesis is returned as authoritative.
    hits = [_hit(clause_id="5usc552-b-exemptions"),
            _hit(clause_id="28cfr16-6-determinations")]
    monkeypatch.setattr(atlas_retriever, "clause_search",
                        lambda query, top_k=5, far_part=None, agency_id=None: hits)
    body_text = ("[5usc552-b-exemptions] exemptions apply. "
                 "[28cfr16-6-determinations] determination basis.")
    monkeypatch.setattr(app_main, "invoke_model",
                        lambda *a, **k: {"body": body_text})
    resp = client.post("/rag/clause-search", json={"query": "exemption"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["needs_review"] is False
    assert body["synthesis"] == body_text


def test_validate_synthesis_citations_helper():
    allowed = {"5usc552-b-exemptions", "28cfr16-6-determinations"}
    # Pass: every bracketed citation is in the allowed set.
    ok, reason = app_main._validate_synthesis_citations(
        "[5usc552-b-exemptions] grounded. [28cfr16-6-determinations] ok.", allowed)
    assert ok is True
    assert reason is None
    # Whitespace inside brackets is stripped before comparison.
    ok, reason = app_main._validate_synthesis_citations(
        "[ 5usc552-b-exemptions ] padded.", allowed)
    assert ok is True
    # Fail: unknown/hallucinated citation.
    ok, reason = app_main._validate_synthesis_citations(
        "[hallucinated-clause] made-up.", allowed)
    assert ok is False
    assert reason
    # Fail: zero bracketed citations.
    ok, reason = app_main._validate_synthesis_citations(
        "uncited summary text", allowed)
    assert ok is False
    assert reason


def test_doc_to_hit_includes_traceability_fields():
    hit = atlas_retriever._doc_to_hit({
        "clause_id": "5usc552-b-exemptions",
        "title": "FOIA Exemptions",
        "score": 2.0,
        "far_part": "5 USC 552",
        "cite": "5 U.S.C. 552(b)",
        "source_file": "5usc552-b-exemptions.md",
        "chunk_index": 3,
        "heading_path": ["T", "S"],
        "text": "x",
    })
    assert hit["chunk_index"] == 3
    assert hit["heading_path"] == ["T", "S"]
    assert hit["cite"] == "5 U.S.C. 552(b)"
    assert hit["source_file"] == "5usc552-b-exemptions.md"


def test_doc_to_hit_bounds_snippet_text(monkeypatch):
    monkeypatch.setattr(atlas_retriever, "SNIPPET_MAX_CHARS", 50)
    hit = atlas_retriever._doc_to_hit({"text": "y" * 500})
    assert len(hit["text"]) == 50


# ---------------------------------------------------------------------------
# Multi-tenant boundary (Item 10): agency_id must thread through retrieval and
# scope the Mongo predicate so one agency cannot retrieve another's precedent
# over the shared foia_precedent collection (REQ-RAG-3).
# ---------------------------------------------------------------------------

class _FakeCollection:
    """Captures the find() filter; returns a chainable empty cursor stub."""

    def __init__(self):
        self.filter = None

    def find(self, filter, projection):
        self.filter = filter
        return self

    def sort(self, *a):
        return self

    def limit(self, n):
        return iter([])


def test_clause_search_forwards_agency_id_to_pymongo(monkeypatch):
    # agency_id is a tenant scope; clause_search must thread it through to the
    # lexical search rather than dropping it (mirrors the far_part test).
    monkeypatch.setattr(atlas_retriever, "ATLAS_HYBRID_ENABLED", False)
    captured = {}

    def _fake_search(query, top_k, far_part=None, agency_id=None):
        captured["query"] = query
        captured["top_k"] = top_k
        captured["far_part"] = far_part
        captured["agency_id"] = agency_id
        return [_hit()]

    monkeypatch.setattr(atlas_retriever, "_pymongo_text_search", _fake_search)
    atlas_retriever.clause_search("x", agency_id="DOJ")
    assert captured["agency_id"] == "DOJ"


def test_endpoint_forwards_agency_id_to_clause_search(monkeypatch):
    # POST body agency_id must reach clause_search as a kwarg.
    captured = {}

    def _fake_clause_search(query, top_k=5, far_part=None, agency_id=None):
        captured["query"] = query
        captured["top_k"] = top_k
        captured["far_part"] = far_part
        captured["agency_id"] = agency_id
        return [_hit()]

    monkeypatch.setattr(atlas_retriever, "clause_search", _fake_clause_search)
    monkeypatch.setattr(app_main, "invoke_model",
                        lambda *a, **k: {"body": "stub synthesis"})
    resp = client.post("/rag/clause-search",
                       json={"query": "exemption", "agency_id": "DOJ"})
    assert resp.status_code == 200
    assert captured["agency_id"] == "DOJ"


def test_pymongo_filter_scopes_to_agency_and_shared(monkeypatch):
    # With agency_id="DOJ" the Mongo predicate must match DOJ docs OR shared
    # (agency_id=None) statute — and NOTHING ELSE. An "EPA" doc has
    # agency_id="EPA", which is in neither branch, proving cross-tenant
    # exclusion at the query level.
    fake = _FakeCollection()
    monkeypatch.setattr(atlas_retriever, "_get_collection", lambda: fake)
    atlas_retriever._pymongo_text_search("q", 5, agency_id="DOJ")
    assert fake.filter["$or"] == [{"agency_id": "DOJ"}, {"agency_id": None}]
    assert "agency_id" not in fake.filter  # scoped via $or, not a bare match


def test_pymongo_filter_failclosed_without_agency(monkeypatch):
    # No agency_id => fail closed: only shared (agency_id=None) statute is
    # retrievable; no agency-scoped doc may leak when there is no tenant
    # context.
    fake = _FakeCollection()
    monkeypatch.setattr(atlas_retriever, "_get_collection", lambda: fake)
    atlas_retriever._pymongo_text_search("q", 5)
    assert fake.filter["agency_id"] is None
    assert "$or" not in fake.filter
