"""
test_atlas_retriever.py — unit tests for app/atlas_retriever.py.

Contract summary (current implementation):
  - _get_collection: raises RetrievalUnavailableError on any infra failure;
    never returns None.
  - _pymongo_text_search: propagates RetrievalUnavailableError from
    _get_collection; wraps PyMongoError as RetrievalUnavailableError;
    never returns [] on failure.
  - clause_search: routes to Atlas ONLY when ATLAS_HYBRID_ENABLED=True AND
    langchain-mongodb is importable; otherwise lexical. Applies MIN_SCORE
    filter on results. Propagates RetrievalUnavailableError.

Covers:
  - _doc_to_hit        — all 9 fields, defaults, score coercion, text truncation
  - _get_collection    — raises on pymongo absent; raises on connection failure;
                         reuses singleton
  - _pymongo_text_search — happy path, RetrievalUnavailableError propagation,
                           top_k and query wiring, far_part filter
  - clause_search      — routing, MIN_SCORE filtering, far_part forwarding,
                         default top_k, error propagation
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

import app.atlas_retriever as retriever
from app.atlas_retriever import RetrievalUnavailableError


@pytest.fixture(autouse=True)
def reset_mongo_client():
    """Isolate the module-level _mongo_client singleton between tests."""
    original = retriever._mongo_client
    retriever._mongo_client = None
    yield
    retriever._mongo_client = original


# ---------------------------------------------------------------------------
# _doc_to_hit
# ---------------------------------------------------------------------------

class TestDocToHit:
    def test_full_doc_maps_all_nine_fields(self) -> None:
        doc = {
            "clause_id": "5USC552-b5",
            "title": "Deliberative-process privilege",
            "score": 0.87,
            "far_part": "5 USC 552",
            "cite": "5 USC 552(b)(5)",
            "source_file": "5usc552-b5.md",
            "chunk_index": 2,
            "heading_path": ["5 USC 552", "Exemptions", "(b)(5)"],
            "text": "The deliberative-process exemption applies...",
        }
        assert retriever._doc_to_hit(doc) == {
            "clause_id": "5USC552-b5",
            "title": "Deliberative-process privilege",
            "score": 0.87,
            "far_part": "5 USC 552",
            "cite": "5 USC 552(b)(5)",
            "source_file": "5usc552-b5.md",
            "chunk_index": 2,
            "heading_path": ["5 USC 552", "Exemptions", "(b)(5)"],
            "text": "The deliberative-process exemption applies...",
        }

    def test_missing_fields_use_safe_defaults(self) -> None:
        hit = retriever._doc_to_hit({})
        assert hit["clause_id"] == ""
        assert hit["title"] == ""
        assert hit["far_part"] == ""
        assert hit["score"] == 0.0
        assert hit["cite"] is None
        assert hit["source_file"] == ""
        assert hit["chunk_index"] is None
        assert hit["heading_path"] == []
        assert hit["text"] == ""

    def test_score_coerced_to_float(self) -> None:
        hit = retriever._doc_to_hit({"score": "0.91"})
        assert isinstance(hit["score"], float)
        assert hit["score"] == pytest.approx(0.91)

    def test_text_truncated_to_snippet_max(self) -> None:
        long_text = "x" * (retriever.SNIPPET_MAX_CHARS + 100)
        hit = retriever._doc_to_hit({"text": long_text})
        assert len(hit["text"]) == retriever.SNIPPET_MAX_CHARS


# ---------------------------------------------------------------------------
# _get_collection
# ---------------------------------------------------------------------------

class TestGetCollection:
    def test_raises_retrieval_error_when_pymongo_unavailable(self) -> None:
        with patch.object(retriever, "_PYMONGO_AVAILABLE", False):
            with pytest.raises(RetrievalUnavailableError, match="pymongo not installed"):
                retriever._get_collection()

    def test_raises_retrieval_error_on_client_construction_failure(self) -> None:
        # PyMongoError must be a real exception class or Python rejects it as
        # an except target. Set it to Exception so the except clause can match.
        mock_pymongo = MagicMock()
        mock_pymongo.errors.PyMongoError = Exception
        mock_pymongo.MongoClient.side_effect = Exception("connection refused")
        with patch.object(retriever, "_PYMONGO_AVAILABLE", True):
            with patch.object(retriever, "pymongo", mock_pymongo, create=True):
                with pytest.raises(RetrievalUnavailableError):
                    retriever._get_collection()

    def test_reuses_existing_client_singleton(self) -> None:
        mock_client = MagicMock()
        retriever._mongo_client = mock_client
        with patch.object(retriever, "_PYMONGO_AVAILABLE", True):
            retriever._get_collection()
        mock_client.__getitem__.assert_called()


# ---------------------------------------------------------------------------
# _pymongo_text_search
# ---------------------------------------------------------------------------

class TestPymongoTextSearch:
    def test_propagates_retrieval_unavailable_from_get_collection(self) -> None:
        with patch.object(retriever, "_get_collection",
                          side_effect=RetrievalUnavailableError("mongo down")):
            with pytest.raises(RetrievalUnavailableError, match="mongo down"):
                retriever._pymongo_text_search("time limits", 5)

    def test_raises_retrieval_error_on_pymongo_query_failure(self) -> None:
        pymongo = pytest.importorskip("pymongo")
        mock_coll = MagicMock()
        mock_coll.find.side_effect = pymongo.errors.OperationFailure("no text index")
        with patch.object(retriever, "_get_collection", return_value=mock_coll):
            with pytest.raises(RetrievalUnavailableError, match="lexical text search failed"):
                retriever._pymongo_text_search("time limits", 5)

    def test_returns_shaped_hits_on_success(self) -> None:
        docs = [
            {
                "clause_id": "5USC552-a6A", "title": "Time limits — 20 working days",
                "score": 0.9, "far_part": "5 USC 552", "cite": "5 USC 552(a)(6)(A)",
                "source_file": "5usc552-a6A.md", "chunk_index": 0,
                "heading_path": ["5 USC 552", "Time limits"], "text": "20 working days...",
            },
        ]
        mock_cursor = MagicMock()
        mock_cursor.__iter__ = MagicMock(return_value=iter(docs))
        mock_coll = MagicMock()
        mock_coll.find.return_value.sort.return_value.limit.return_value = mock_cursor

        with patch.object(retriever, "_get_collection", return_value=mock_coll):
            result = retriever._pymongo_text_search("time limits", 5)

        assert len(result) == 1
        assert result[0]["clause_id"] == "5USC552-a6A"
        assert result[0]["cite"] == "5 USC 552(a)(6)(A)"
        assert result[0]["heading_path"] == ["5 USC 552", "Time limits"]

    def test_passes_top_k_to_limit(self) -> None:
        mock_cursor = MagicMock()
        mock_cursor.__iter__ = MagicMock(return_value=iter([]))
        mock_coll = MagicMock()
        mock_coll.find.return_value.sort.return_value.limit.return_value = mock_cursor

        with patch.object(retriever, "_get_collection", return_value=mock_coll):
            retriever._pymongo_text_search("exemptions", top_k=3)

        mock_coll.find.return_value.sort.return_value.limit.assert_called_once_with(3)

    def test_passes_query_to_text_operator(self) -> None:
        mock_cursor = MagicMock()
        mock_cursor.__iter__ = MagicMock(return_value=iter([]))
        mock_coll = MagicMock()
        mock_coll.find.return_value.sort.return_value.limit.return_value = mock_cursor

        with patch.object(retriever, "_get_collection", return_value=mock_coll):
            retriever._pymongo_text_search("foreseeable harm standard", 5)

        call_filter = mock_coll.find.call_args[0][0]
        assert call_filter["$text"] == {"$search": "foreseeable harm standard"}

    def test_far_part_added_to_filter_when_provided(self) -> None:
        mock_cursor = MagicMock()
        mock_cursor.__iter__ = MagicMock(return_value=iter([]))
        mock_coll = MagicMock()
        mock_coll.find.return_value.sort.return_value.limit.return_value = mock_cursor

        with patch.object(retriever, "_get_collection", return_value=mock_coll):
            retriever._pymongo_text_search("time limits", 5, far_part="5 USC 552")

        call_filter = mock_coll.find.call_args[0][0]
        assert call_filter["far_part"] == "5 USC 552"

    def test_far_part_absent_from_filter_when_not_provided(self) -> None:
        mock_cursor = MagicMock()
        mock_cursor.__iter__ = MagicMock(return_value=iter([]))
        mock_coll = MagicMock()
        mock_coll.find.return_value.sort.return_value.limit.return_value = mock_cursor

        with patch.object(retriever, "_get_collection", return_value=mock_coll):
            retriever._pymongo_text_search("time limits", 5)

        call_filter = mock_coll.find.call_args[0][0]
        assert "far_part" not in call_filter


# ---------------------------------------------------------------------------
# clause_search (routing, filtering, error propagation)
# ---------------------------------------------------------------------------

class TestClauseSearch:
    def test_delegates_to_pymongo_when_langchain_absent(self) -> None:
        hits = [{"clause_id": "x", "score": 99.0}]
        with patch.object(retriever, "_LANGCHAIN_MONGODB_AVAILABLE", False):
            with patch.object(retriever, "_pymongo_text_search", return_value=hits) as mock_lex:
                result = retriever.clause_search("time limits", top_k=3)
        mock_lex.assert_called_once_with("time limits", 3, far_part=None)
        assert result == hits

    def test_delegates_to_atlas_when_enabled_and_langchain_present(self) -> None:
        with patch.object(retriever, "ATLAS_HYBRID_ENABLED", True):
            with patch.object(retriever, "_LANGCHAIN_MONGODB_AVAILABLE", True):
                with patch.object(retriever, "_atlas_hybrid_search", return_value=[]) as mock_atlas:
                    retriever.clause_search("exemptions", top_k=5)
        mock_atlas.assert_called_once_with("exemptions", 5, far_part=None)

    def test_stays_on_lexical_when_langchain_present_but_hybrid_not_enabled(self) -> None:
        hits = [{"clause_id": "y", "score": 99.0}]
        with patch.object(retriever, "ATLAS_HYBRID_ENABLED", False):
            with patch.object(retriever, "_LANGCHAIN_MONGODB_AVAILABLE", True):
                with patch.object(retriever, "_pymongo_text_search", return_value=hits) as mock_lex:
                    with patch.object(retriever, "_atlas_hybrid_search") as mock_atlas:
                        retriever.clause_search("query")
        mock_lex.assert_called_once()
        mock_atlas.assert_not_called()

    def test_min_score_filter_drops_low_confidence_hits(self) -> None:
        hits = [
            {"clause_id": "a", "score": 0.5},
            {"clause_id": "b", "score": retriever.MIN_SCORE},
            {"clause_id": "c", "score": retriever.MIN_SCORE + 1.0},
        ]
        with patch.object(retriever, "_LANGCHAIN_MONGODB_AVAILABLE", False):
            with patch.object(retriever, "_pymongo_text_search", return_value=hits):
                result = retriever.clause_search("query")
        returned_ids = [h["clause_id"] for h in result]
        assert "a" not in returned_ids
        assert "b" in returned_ids
        assert "c" in returned_ids

    def test_propagates_retrieval_error_when_mongo_unreachable(self) -> None:
        with patch.object(retriever, "_LANGCHAIN_MONGODB_AVAILABLE", False):
            with patch.object(retriever, "_pymongo_text_search",
                              side_effect=RetrievalUnavailableError("mongo down")):
                with pytest.raises(RetrievalUnavailableError):
                    retriever.clause_search("exemptions")

    def test_far_part_forwarded_to_search(self) -> None:
        with patch.object(retriever, "_LANGCHAIN_MONGODB_AVAILABLE", False):
            with patch.object(retriever, "_pymongo_text_search", return_value=[]) as mock_lex:
                retriever.clause_search("time limits", far_part="5 USC 552")
        mock_lex.assert_called_once_with("time limits", 5, far_part="5 USC 552")

    def test_default_top_k_is_five(self) -> None:
        with patch.object(retriever, "_LANGCHAIN_MONGODB_AVAILABLE", False):
            with patch.object(retriever, "_pymongo_text_search", return_value=[]) as mock_lex:
                retriever.clause_search("query")
        _, called_top_k = mock_lex.call_args[0]
        assert called_top_k == 5
