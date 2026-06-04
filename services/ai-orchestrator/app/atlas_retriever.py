"""
atlas_retriever.py — retrieval integration for FOIA precedent corpus.

CURRENT STATE: stub with pymongo lexical fallback.

TODO (W2 RAG work — must complete before Atlas hybrid search works):
  1. Add `langchain-mongodb>=0.2` to requirements.txt — NOT present yet.
  2. Add `MONGO_DB` env var to ai-orchestrator in infra/docker/docker-compose.yml
     (foia-request-service and redaction-review-service already have it; ai-orchestrator
     gets only MONGO_URL today).
  3. Create Atlas Search index on the `foia_precedent` collection:
       { "mappings": { "dynamic": false, "fields": {
           "text": [{"type": "string"}, {"type": "knnVector", "dimensions": 512, "similarity": "cosine"}]
       }}}
  4. Run the FOIA corpus indexer (scripts/index-foia-corpus.py — see proposal below).
  5. Replace _atlas_hybrid_search() stub body with real MongoDBAtlasVectorSearch wiring.
  6. Set ATLAS_HYBRID_ENABLED=true (env) once the hybrid path is wired AND tested —
     import availability alone never routes to it (see clause_search).

Missing that blocks Atlas hybrid search:
  - langchain-mongodb (not in requirements.txt)
  - Atlas vector index on foia_precedent collection (not created)
  - Indexed corpus (foia_precedent collection empty)
  - MONGO_DB env var missing from ai-orchestrator docker-compose entry
"""
from __future__ import annotations

import logging
import os
from typing import Any

log = logging.getLogger("ai-orchestrator.atlas_retriever")

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://app:app_dev_password@localhost:27017")
MONGO_DB = os.environ.get("MONGO_DB", "foia_response_pipeline")
COLLECTION_FOIA_PRECEDENT = "foia_precedent"

# Confidence bar for retrieval (FOIA-conservative: weak hits are not usable
# precedent — docs/retrieval-plan.md escalation rule + REQ-RAG-2 in
# docs/prd/phase-1-ai-adoption.md). Defaults are provisional pending the W2
# retrieval-eval pass; tune via env without a code change.
MIN_SCORE = float(os.environ.get("CLAUSE_SEARCH_MIN_SCORE", "1.0"))
MIN_HITS = int(os.environ.get("CLAUSE_SEARCH_MIN_HITS", "1"))

# Bounds hit text in responses/prompts; chunks are budgeted ~800 chars by the
# indexer, so this only truncates pathological docs.
SNIPPET_MAX_CHARS = int(os.environ.get("CLAUSE_SEARCH_SNIPPET_MAX_CHARS", "1200"))

# Atlas hybrid search must be EXPLICITLY enabled once wired (W2 TODO item 6
# above). Routing on import availability alone would silently bypass the
# working lexical path the moment langchain-mongodb lands in requirements.txt
# — _atlas_hybrid_search is still a stub returning [].
ATLAS_HYBRID_ENABLED = os.environ.get("ATLAS_HYBRID_ENABLED", "").lower() in ("1", "true", "yes")


class RetrievalUnavailableError(RuntimeError):
    """
    Retrieval infrastructure failure — Mongo unreachable, missing text index,
    auth failure. Distinct from a search that ran and matched nothing: callers
    must surface this as a degraded state, never as an empty-but-OK result.
    """

try:
    from langchain_mongodb import MongoDBAtlasVectorSearch  # type: ignore[import]
    _LANGCHAIN_MONGODB_AVAILABLE = True
except ImportError:
    _LANGCHAIN_MONGODB_AVAILABLE = False
    log.warning(
        "langchain-mongodb not installed — Atlas hybrid search unavailable. "
        "langchain-mongodb==0.11.0 is in requirements.txt; reinstall to enable."
    )

try:
    import pymongo
    _PYMONGO_AVAILABLE = True
except ImportError:  # pragma: no cover
    _PYMONGO_AVAILABLE = False

_mongo_client = None


def _get_collection():
    global _mongo_client
    if not _PYMONGO_AVAILABLE:
        raise RetrievalUnavailableError(
            "pymongo not installed — lexical retrieval unavailable"
        )
    try:
        if _mongo_client is None:
            _mongo_client = pymongo.MongoClient(MONGO_URL, serverSelectionTimeoutMS=1000)
        return _mongo_client[MONGO_DB][COLLECTION_FOIA_PRECEDENT]
    except pymongo.errors.PyMongoError as exc:
        log.warning("MongoDB connection failed: %s", exc)
        raise RetrievalUnavailableError(f"MongoDB connection failed: {exc}") from exc


def clause_search(query: str, top_k: int = 5, far_part: str | None = None) -> list[dict[str, Any]]:
    """
    Search the FOIA precedent corpus; return hit records shaped for /rag/clause-search.

    Each hit: {clause_id, title, score, far_part, cite, source_file, chunk_index, heading_path, text}
    (text bounded to SNIPPET_MAX_CHARS).

    When far_part is provided, hits are restricted to that far_part cite prefix (exact match).

    Resolution order:
      1. Atlas hybrid search — ONLY when ATLAS_HYBRID_ENABLED is set (the
         hybrid path is still a stub; import availability alone never routes
         to it).
      2. pymongo $text lexical search.

    Hits scoring below MIN_SCORE are dropped (confidence bar). An empty list
    means the search ran and found nothing usable; infrastructure failure
    raises RetrievalUnavailableError instead.
    """
    if ATLAS_HYBRID_ENABLED and _LANGCHAIN_MONGODB_AVAILABLE:
        hits = _atlas_hybrid_search(query, top_k, far_part=far_part)
    else:
        hits = _pymongo_text_search(query, top_k, far_part=far_part)
    return [hit for hit in hits if hit["score"] >= MIN_SCORE]


def _atlas_hybrid_search(query: str, top_k: int, far_part: str | None = None) -> list[dict[str, Any]]:
    """
    Atlas hybrid search via MongoDBAtlasVectorSearch + Titan v2 512-d embeddings.

    Requires:
      - langchain-mongodb installed (import guard above)
      - ATLAS_HYBRID_ENABLED=true env var (routing guard in clause_search)
      - Atlas Search index "foia_precedent_vector" on the foia_precedent collection:
          {"mappings": {"dynamic": false, "fields": {
              "text": [{"type": "string"},
                       {"type": "knnVector", "dimensions": 512, "similarity": "cosine"}]
          }}}
      - Corpus indexed with embeddings (scripts/index-foia-corpus.py --upsert
        after adding Titan embedding generation to that script)

    far_part is applied as a post-filter on the returned docs; Atlas pre-filter
    support requires an $vectorSearch pipeline stage (W3 upgrade path).
    """
    import boto3

    AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

    try:
        from langchain_aws import BedrockEmbeddings
    except ImportError as exc:
        raise RetrievalUnavailableError(
            "langchain-aws not installed — required for Titan v2 embeddings"
        ) from exc

    embeddings = BedrockEmbeddings(
        client=boto3.client("bedrock-runtime", region_name=AWS_REGION),
        model_id="amazon.titan-embed-text-v2:0",
        model_kwargs={"dimensions": 512, "normalize": True},
    )
    store = MongoDBAtlasVectorSearch(
        collection=_get_collection(),
        embedding=embeddings,
        index_name="foia_precedent_vector",
        text_key="text",
        embedding_key="embedding",
    )
    search_kwargs: dict[str, Any] = {"k": top_k}
    if far_part:
        search_kwargs["pre_filter"] = {"far_part": {"$eq": far_part}}
    lc_retriever = store.as_retriever(
        search_type="similarity",
        search_kwargs=search_kwargs,
    )
    try:
        docs = lc_retriever.invoke(query)
    except Exception as exc:
        log.warning("Atlas hybrid search failed: %s", exc)
        raise RetrievalUnavailableError(f"Atlas hybrid search failed: {exc}") from exc
    return [_doc_to_hit(doc.metadata | {"text": doc.page_content}) for doc in docs]


def _pymongo_text_search(query: str, top_k: int, far_part: str | None = None) -> list[dict[str, Any]]:
    """
    Lexical fallback via pymongo $text operator.

    Requires a text index on foia_precedent — the corpus indexer must have run.
    Raises RetrievalUnavailableError on infrastructure failure (Mongo
    unreachable, missing text index, auth failure) so callers can distinguish
    "retrieval is broken" from "search ran, no matches". Programming errors
    propagate unwrapped.
    """
    coll = _get_collection()
    filter = {"$text": {"$search": query}}
    if far_part:
        filter["far_part"] = far_part
    try:
        cursor = (
            coll.find(
                filter,
                {
                    "score": {"$meta": "textScore"},
                    "clause_id": 1,
                    "title": 1,
                    "far_part": 1,
                    "cite": 1,
                    "source_file": 1,
                    "chunk_index": 1,
                    "heading_path": 1,
                    "text": 1,
                },
            )
            .sort([("score", {"$meta": "textScore"})])
            .limit(top_k)
        )
        return [_doc_to_hit(doc) for doc in cursor]
    except pymongo.errors.PyMongoError as exc:
        log.warning("pymongo text search failed: %s", exc)
        raise RetrievalUnavailableError(f"lexical text search failed: {exc}") from exc


def _doc_to_hit(doc: dict[str, Any]) -> dict[str, Any]:
    """Normalize a MongoDB document to the /rag/clause-search hit contract."""
    return {
        "clause_id": doc.get("clause_id", ""),
        "title": doc.get("title", ""),
        "score": float(doc.get("score", 0.0)),
        "far_part": doc.get("far_part", ""),
        # Grounding metadata — the synthesis prompt and reviewer traceability
        # (docs/hitl-plan.md) need the source text + citation, not just ids.
        "cite": doc.get("cite"),
        "source_file": doc.get("source_file", ""),
        "chunk_index": doc.get("chunk_index"),
        "heading_path": doc.get("heading_path", []),
        "text": (doc.get("text", "") or "")[:SNIPPET_MAX_CHARS],
    }
