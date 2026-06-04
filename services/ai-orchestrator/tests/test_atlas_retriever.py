"""
test_atlas_retriever.py — unit tests for app/atlas_retriever.py.

Covers every fallback tier in the resolution chain:
  1. _doc_to_hit        — field normalization and missing-field defaults
  2. _get_collection    — returns None when pymongo absent or connection raises
  3. _pymongo_text_search — happy path, unreachable DB, missing text index, top_k
  4. clause_search      — routing: langchain absent → lexical; langchain present → atlas stub
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

import app.atlas_retriever as retriever


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
    def test_full_doc_maps_all_fields(self) -> None:
        doc = {
            "clause_id": "5USC552-b5",
            "title": "Deliberative-process privilege",
            "score": 0.87,
            "far_part": "5 USC 552",
        }
        assert retriever._doc_to_hit(doc) == {
            "clause_id": "5USC552-b5",
            "title": "Deliberative-process privilege",
            "score": 0.87,
            "far_part": "5 USC 552",
        }

    def test_missing_fields_default_to_empty_string_and_zero(self) -> None:
        hit = retriever._doc_to_hit({})
        assert hit["clause_id"] == ""
        assert hit["title"] == ""
        assert hit["far_part"] == ""
        assert hit["score"] == 0.0

    def test_score_coerced_to_float(self) -> None:
        hit = retriever._doc_to_hit({"score": "0.91"})
        assert isinstance(hit["score"], float)
        assert hit["score"] == pytest.approx(0.91)


# ---------------------------------------------------------------------------
# _get_collection
# ---------------------------------------------------------------------------

class TestGetCollection:
    def test_returns_none_when_pymongo_unavailable(self) -> None:
        with patch.object(retriever, "_PYMONGO_AVAILABLE", False):
            result = retriever._get_collection()
        assert result is None

    def test_returns_none_on_client_construction_failure(self) -> None:
        # patch.object with create=True injects a fake `pymongo` into the module
        # namespace, covering environments where pymongo isn't installed.
        mock_pymongo = MagicMock()
        mock_pymongo.MongoClient.side_effect = Exception("connection refused")
        with patch.object(retriever, "_PYMONGO_AVAILABLE", True):
            with patch.object(retriever, "pymongo", mock_pymongo, create=True):
                result = retriever._get_collection()
        assert result is None

    def test_reuses_existing_client_singleton(self) -> None:
        mock_client = MagicMock()
        retriever._mongo_client = mock_client
        with patch.object(retriever, "_PYMONGO_AVAILABLE", True):
            retriever._get_collection()
        # MongoClient constructor must NOT have been called again
        mock_client.__getitem__.assert_called()


# ---------------------------------------------------------------------------
# _pymongo_text_search
# ---------------------------------------------------------------------------

class TestPymongoTextSearch:
    def test_returns_empty_when_collection_is_none(self) -> None:
        with patch.object(retriever, "_get_collection", return_value=None):
            assert retriever._pymongo_text_search("time limits", 5) == []

    def test_returns_empty_when_text_query_raises(self) -> None:
        mock_coll = MagicMock()
        mock_coll.find.side_effect = Exception("no text index on collection")
        with patch.object(retriever, "_get_collection", return_value=mock_coll):
            assert retriever._pymongo_text_search("time limits", 5) == []

    def test_returns_shaped_hits_on_success(self) -> None:
        docs = [
            {"clause_id": "5USC552-a6A", "title": "Time limits — 20 working days",
             "score": 0.9, "far_part": "5 USC 552"},
            {"clause_id": "5USC552-b5", "title": "Deliberative-process privilege",
             "score": 0.8, "far_part": "5 USC 552"},
        ]
        mock_cursor = MagicMock()
        mock_cursor.__iter__ = MagicMock(return_value=iter(docs))
        mock_coll = MagicMock()
        mock_coll.find.return_value.sort.return_value.limit.return_value = mock_cursor

        with patch.object(retriever, "_get_collection", return_value=mock_coll):
            result = retriever._pymongo_text_search("time limits", 5)

        assert len(result) == 2
        assert result[0]["clause_id"] == "5USC552-a6A"
        assert result[1]["clause_id"] == "5USC552-b5"
        assert result[0]["score"] == pytest.approx(0.9)

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
        assert call_filter == {"$text": {"$search": "foreseeable harm standard"}}


# ---------------------------------------------------------------------------
# clause_search (routing)
# ---------------------------------------------------------------------------

class TestClauseSearch:
    def test_delegates_to_pymongo_when_langchain_absent(self) -> None:
        with patch.object(retriever, "_LANGCHAIN_MONGODB_AVAILABLE", False):
            with patch.object(retriever, "_pymongo_text_search", return_value=[{"clause_id": "x"}]) as mock_lex:
                result = retriever.clause_search("time limits", top_k=3)
        mock_lex.assert_called_once_with("time limits", 3)
        assert result == [{"clause_id": "x"}]

    def test_delegates_to_atlas_when_langchain_present(self) -> None:
        with patch.object(retriever, "_LANGCHAIN_MONGODB_AVAILABLE", True):
            with patch.object(retriever, "_atlas_hybrid_search", return_value=[]) as mock_atlas:
                result = retriever.clause_search("exemptions", top_k=5)
        mock_atlas.assert_called_once_with("exemptions", 5)
        assert result == []

    def test_returns_empty_list_when_mongo_unreachable(self) -> None:
        with patch.object(retriever, "_LANGCHAIN_MONGODB_AVAILABLE", False):
            with patch.object(retriever, "_get_collection", return_value=None):
                result = retriever.clause_search("exemptions")
        assert result == []

    def test_default_top_k_is_five(self) -> None:
        with patch.object(retriever, "_LANGCHAIN_MONGODB_AVAILABLE", False):
            with patch.object(retriever, "_pymongo_text_search", return_value=[]) as mock_lex:
                retriever.clause_search("query")
        _, called_top_k = mock_lex.call_args[0]
        assert called_top_k == 5
