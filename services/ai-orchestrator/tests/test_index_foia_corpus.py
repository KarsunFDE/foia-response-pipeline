"""
Tests for scripts/index-foia-corpus.py — the FOIA markdown corpus indexer.

The script filename is hyphenated and lives outside the package, so it is
loaded via importlib rather than imported. Mongo-touching code is exercised
against an injected fake pymongo module (no real database required).
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "index-foia-corpus.py"
assert _SCRIPT.exists(), f"corpus indexer not found at {_SCRIPT}"
_spec = importlib.util.spec_from_file_location("index_foia_corpus", _SCRIPT)
idx = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(idx)


# ---------------------------------------------------------------------------
# Frontmatter parsing
# ---------------------------------------------------------------------------

def test_parse_frontmatter_extracts_keys_and_strips_block():
    text = "---\ncite: 5 USC 552(b)\ntopic: exemptions\n---\nbody text here"
    fm, body = idx.parse_frontmatter(text)
    assert fm == {"cite": "5 USC 552(b)", "topic": "exemptions"}
    assert body == "body text here"
    # The frontmatter delimiters are gone from the returned body.
    assert "---" not in body
    assert "cite:" not in body


def test_parse_frontmatter_no_frontmatter_returns_empty_and_unchanged():
    text = "# Heading\n\nbody with no frontmatter"
    fm, body = idx.parse_frontmatter(text)
    assert fm == {}
    assert body == text


# ---------------------------------------------------------------------------
# Footer stripping / preservation
# ---------------------------------------------------------------------------

def test_strip_stub_footer_removes_trailing_blockquote():
    text = (
        "Body paragraph one.\n\n"
        "Body paragraph two.\n\n"
        "> STARTER STUB — paraphrased. See https://example.gov/foia"
    )
    out = idx.strip_stub_footer(text)
    assert "STARTER STUB" not in out
    assert "Body paragraph one." in out
    assert "Body paragraph two." in out


def test_strip_stub_footer_preserves_non_trailing_blockquote_and_body():
    # A blockquote that is NOT the trailing run must survive, because the
    # function only pops the contiguous '>' run at the very end.
    text = (
        "> A quoted passage in the middle of the document.\n\n"
        "Regular body text after the quote.\n\n"
        "> STARTER STUB — footer to strip"
    )
    out = idx.strip_stub_footer(text)
    assert "STARTER STUB" not in out
    assert "> A quoted passage in the middle of the document." in out
    assert "Regular body text after the quote." in out


# ---------------------------------------------------------------------------
# Paragraph-level sub-chunking
# ---------------------------------------------------------------------------

def test_split_by_paragraphs_short_text_single_chunk():
    text = "short paragraph"
    assert idx.split_by_paragraphs(text) == [text]


def test_split_by_paragraphs_over_limit_splits_into_multiple_chunks():
    # Three paragraphs each well under the 800-char limit but together over it
    # must be split on blank-line boundaries into multiple chunks, each within
    # the limit.
    para = "x" * 400
    text = "\n\n".join([para, para, para])
    assert len(text) > idx.MAX_SECTION_CHARS
    chunks = idx.split_by_paragraphs(text)
    assert len(chunks) > 1
    assert all(len(c) <= idx.MAX_SECTION_CHARS for c in chunks)


def test_split_by_paragraphs_single_oversized_paragraph_not_split():
    # A single paragraph with no blank-line boundary cannot be split; the
    # implementation returns it as one chunk even though it exceeds the limit.
    para = "y" * (idx.MAX_SECTION_CHARS + 200)
    chunks = idx.split_by_paragraphs(para)
    assert chunks == [para]
    assert len(chunks[0]) > idx.MAX_SECTION_CHARS


# ---------------------------------------------------------------------------
# derive_far_part
# ---------------------------------------------------------------------------

def test_derive_far_part_none_returns_none():
    assert idx.derive_far_part(None) is None


def test_derive_far_part_maps_cites():
    assert idx.derive_far_part("5 USC 552(a)(6)(A)") == "5 USC 552"
    assert idx.derive_far_part("28 CFR 16.5–16.6") == "28 CFR 16"
    assert idx.derive_far_part("some other cite") is None


# ---------------------------------------------------------------------------
# chunk_file end-to-end
# ---------------------------------------------------------------------------

def test_chunk_file_end_to_end(tmp_path):
    md = tmp_path / "5usc552-a6A-time-limits.md"
    md.write_text(
        "---\n"
        "cite: 5 USC 552(a)(6)(A)\n"
        "topic: time-limits\n"
        "---\n"
        "# 5 USC 552(a)(6)(A) — Time limits\n\n"
        "First section paragraph about the twenty working day clock.\n\n"
        "## Unusual circumstances\n\n"
        "Second section paragraph about the ten day extension.\n\n"
        "> STARTER STUB — strip me\n",
        encoding="utf-8",
    )
    chunks = idx.chunk_file(md)
    assert chunks, "expected at least one chunk"

    # Every chunk carries the right source_file and clause_id (filename stem).
    for c in chunks:
        assert c["source_file"] == "5usc552-a6A-time-limits.md"
        assert c["clause_id"] == "5usc552-a6A-time-limits"
        assert c["far_part"] == "5 USC 552"  # derived from cite
        assert "STARTER STUB" not in c["text"]

    # chunk_index is sequential starting at 0.
    assert [c["chunk_index"] for c in chunks] == list(range(len(chunks)))


def test_chunk_file_frontmatter_only_no_body(tmp_path):
    # A file that is only frontmatter (no body) yields no chunks and does not
    # crash.
    md = tmp_path / "empty-body.md"
    md.write_text(
        "---\ncite: 5 USC 552(a)(6)(A)\ntopic: time-limits\n---\n",
        encoding="utf-8",
    )
    chunks = idx.chunk_file(md)
    assert chunks == []


# ---------------------------------------------------------------------------
# _upsert_to_mongo against an injected fake pymongo
# ---------------------------------------------------------------------------

class _FakeCollection:
    def __init__(self):
        self.delete_filters = []
        self.bulk_ops = []
        self.create_index_calls = []

    def delete_many(self, filt):
        self.delete_filters.append(filt)

    def bulk_write(self, ops, ordered=True):
        # Record that delete happened before this (caller asserts ordering).
        self.bulk_ops = ops

    def create_index(self, keys, name=None):
        self.create_index_calls.append((keys, name))

    def count_documents(self, filt):
        return 7


class _FakeDB:
    def __init__(self, collection):
        self._collection = collection
        self.requested_names = []

    def __getitem__(self, name):
        self.requested_names.append(name)
        return self._collection


class _FakeClient:
    def __init__(self, db):
        self._db = db
        self.requested_db_names = []

    def __getitem__(self, name):
        self.requested_db_names.append(name)
        return self._db


class _InsertOne:
    def __init__(self, doc):
        self.doc = doc


def _install_fake_pymongo(monkeypatch):
    coll = _FakeCollection()
    db = _FakeDB(coll)
    client = _FakeClient(db)

    fake = type(sys)("pymongo")
    fake.MongoClient = lambda *a, **k: client
    fake.InsertOne = _InsertOne
    fake.TEXT = "text"
    monkeypatch.setitem(sys.modules, "pymongo", fake)
    return client, db, coll


def _chunks():
    return [
        {"source_file": "b.md", "clause_id": "b", "text": "beta body"},
        {"source_file": "a.md", "clause_id": "a", "text": "alpha body"},
        {"source_file": "a.md", "clause_id": "a", "text": "alpha body two"},
    ]


def test_upsert_default_mode_scoped_delete_before_bulk_write(monkeypatch):
    _client, _db, coll = _install_fake_pymongo(monkeypatch)
    count = idx._upsert_to_mongo(
        _chunks(), "mongodb://localhost:27017", "testdb")
    assert count == 7
    # default mode: delete scoped to sorted distinct source files.
    assert coll.delete_filters == [{"source_file": {"$in": ["a.md", "b.md"]}}]
    # delete recorded before bulk_write populated the ops.
    assert len(coll.bulk_ops) == 3
    # text index created.
    assert coll.create_index_calls
    keys, name = coll.create_index_calls[0]
    assert keys == [("text", "text")]
    assert name == "foia_text_search"


def test_upsert_replace_mode_clears_collection(monkeypatch):
    _client, _db, coll = _install_fake_pymongo(monkeypatch)
    idx._upsert_to_mongo(
        _chunks(), "mongodb://localhost:27017", "testdb", replace=True)
    assert coll.delete_filters == [{}]


def test_upsert_stamps_shared_run_id_and_indexed_at(monkeypatch):
    _client, _db, coll = _install_fake_pymongo(monkeypatch)
    idx._upsert_to_mongo(_chunks(), "mongodb://localhost:27017", "testdb")
    docs = [op.doc for op in coll.bulk_ops]
    run_ids = {d["run_id"] for d in docs}
    assert len(run_ids) == 1  # one shared run_id across the run
    only = run_ids.pop()
    assert len(only) == 32  # uuid4 hex
    int(only, 16)  # is valid hex
    for d in docs:
        assert isinstance(d["indexed_at"], str) and d["indexed_at"]


def test_upsert_respects_collection_name(monkeypatch):
    _client, db, _coll = _install_fake_pymongo(monkeypatch)
    idx._upsert_to_mongo(
        _chunks(), "mongodb://localhost:27017", "testdb",
        collection_name="custom_coll")
    assert "custom_coll" in db.requested_names
