"""
Tests for scripts/index-foia-corpus.py — the FOIA markdown corpus indexer.

The script filename is hyphenated and lives outside the package, so it is
loaded via importlib rather than imported. Mongo-touching code is exercised
against an injected fake pymongo module (no real database required).
"""
from __future__ import annotations

import importlib.util
import sys
import types
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
    # A blockquote that is NOT the footer must survive, because the function
    # only pops trailing blank lines and lines matching the '> STARTER STUB ...'
    # pattern, not arbitrary '>' blockquote lines.
    text = (
        "> A quoted passage in the middle of the document.\n\n"
        "Regular body text after the quote.\n\n"
        "> STARTER STUB — footer to strip"
    )
    out = idx.strip_stub_footer(text)
    assert "STARTER STUB" not in out
    assert "> A quoted passage in the middle of the document." in out
    assert "Regular body text after the quote." in out


def test_strip_stub_footer_preserves_trailing_legitimate_blockquote():
    # A legitimate quoted statutory excerpt immediately before the stub footer
    # must survive — only the '> STARTER STUB ...' line is provenance to drop.
    text = (
        "Body paragraph.\n\n"
        '> "Records compiled for law enforcement purposes..." 5 USC 552(b)(7)\n\n'
        "> STARTER STUB — paraphrased. See https://example.gov"
    )
    out = idx.strip_stub_footer(text)
    assert "STARTER STUB" not in out
    assert '> "Records compiled for law enforcement purposes..." 5 USC 552(b)(7)' in out


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


def test_split_by_paragraphs_single_oversized_paragraph_hard_split():
    # A single paragraph with no blank-line boundary that exceeds max_chars is
    # hard-split at sentence boundaries; no chunk exceeds the limit and every
    # sentence's distinctive token survives in at least one chunk.
    sentences = [f"Sentence number tokenword{i} expands the passage." for i in range(40)]
    para = " ".join(sentences)
    assert len(para) > 1800
    chunks = idx.split_by_paragraphs(para, max_chars=300)
    assert len(chunks) > 1
    assert all(len(c) <= 300 for c in chunks)
    joined = "\n".join(chunks)
    for i in range(40):
        assert f"tokenword{i}" in joined


def test_hard_split_character_fallback_with_overlap():
    # A single 1000-char "sentence" with no sentence punctuation cannot split
    # at a sentence boundary, so it falls back to a sliding character window:
    # all chunks within the limit and consecutive chunks share an overlap.
    text = "x" * 1000
    result = idx._hard_split(text, max_chars=300)
    assert len(result) > 1
    assert all(len(c) <= 300 for c in result)
    # step = max_chars - overlap = 300 - 100 = 200, so the second chunk starts
    # 200 chars in and shares the trailing 100 chars of the first.
    assert result[0][-100:] in result[1]


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

class _FakeBulkWriteError(Exception):
    def __init__(self, details):
        super().__init__("fake bulk write error")
        self.details = details


class _FakeCollection:
    def __init__(self):
        self.delete_filters = []
        self.bulk_ops = []
        self.create_index_calls = []
        # When set, bulk_write raises this after recording its ops.
        self.bulk_write_error = None

    def delete_many(self, filt):
        self.delete_filters.append(filt)

    def bulk_write(self, ops, ordered=True):
        # Record that delete happened before this (caller asserts ordering).
        self.bulk_ops = ops
        if self.bulk_write_error is not None:
            raise self.bulk_write_error

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
    # Real pymongo exposes BulkWriteError under pymongo.errors; mirror that so
    # the impl's `except pymongo.errors.BulkWriteError` resolves.
    fake.errors = types.SimpleNamespace(BulkWriteError=_FakeBulkWriteError)
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


def test_upsert_partial_bulk_failure_cleans_up_run(monkeypatch):
    _client, _db, coll = _install_fake_pymongo(monkeypatch)
    coll.bulk_write_error = _FakeBulkWriteError(
        details={"writeErrors": [{"index": 1, "errmsg": "dup"}]}
    )
    chunks = [
        {"source_file": "a.md", "chunk_index": 0, "text": "alpha"},
        {"source_file": "a.md", "chunk_index": 1, "text": "beta"},
    ]

    with pytest.raises(RuntimeError) as excinfo:
        idx._upsert_to_mongo(chunks, "mongodb://localhost", "db")

    # (a) message mentions cleanup and the write-error count.
    msg = str(excinfo.value)
    assert "cleaned up partial run" in msg
    assert "1 write error(s)" in msg

    # (b) a run_id-scoped delete_many ran AFTER the bulk_write attempt.
    assert coll.bulk_ops, "bulk_write should have been attempted"
    run_id = coll.bulk_ops[0].doc["run_id"]
    assert coll.delete_filters[-1] == {"run_id": run_id}
    assert len(run_id) == 32
    int(run_id, 16)  # valid hex

    # (c) the text index was never created after a failed load.
    assert coll.create_index_calls == []

    # (d) exception chaining preserved.
    assert excinfo.value.__cause__ is coll.bulk_write_error


# ---------------------------------------------------------------------------
# Real-corpus budget enforcement
# ---------------------------------------------------------------------------

def test_split_by_paragraphs_no_chunk_exceeds_budget_on_real_corpus():
    # The b-exemptions file historically carried a single 1236-char paragraph
    # that passed through whole; every chunk must now stay within the budget.
    repo_root = Path(__file__).resolve().parents[3]
    path = repo_root / "data" / "seed" / "foia-precedent" / "5usc552-b-exemptions.md"
    assert path.exists(), f"corpus file not found at {path}"
    chunks = idx.chunk_file(path)
    assert chunks, "expected at least one chunk"
    for c in chunks:
        assert len(c["text"]) <= idx.MAX_SECTION_CHARS
