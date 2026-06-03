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

# TODO: once langchain-mongodb is in requirements.txt, replace this block with:
#   from langchain_mongodb import MongoDBAtlasVectorSearch
#   from langchain_aws import BedrockEmbeddings
try:
    from langchain_mongodb import MongoDBAtlasVectorSearch  # type: ignore[import]
    _LANGCHAIN_MONGODB_AVAILABLE = True
except ImportError:
    _LANGCHAIN_MONGODB_AVAILABLE = False
    log.warning(
        "langchain-mongodb not installed — Atlas hybrid search unavailable. "
        "Add langchain-mongodb to requirements.txt to enable."
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
        return None
    try:
        if _mongo_client is None:
            _mongo_client = pymongo.MongoClient(MONGO_URL, serverSelectionTimeoutMS=1000)
        return _mongo_client[MONGO_DB][COLLECTION_FOIA_PRECEDENT]
    except Exception as exc:
        log.warning("MongoDB connection failed: %s", exc)
        return None


def clause_search(query: str, top_k: int = 5) -> list[dict[str, Any]]:
    """
    Search the FOIA precedent corpus; return hit records shaped for /rag/clause-search.

    Each hit: {clause_id: str, title: str, score: float, far_part: str}

    Resolution order:
      1. Atlas hybrid search (langchain-mongodb + vector index) — not yet available.
      2. pymongo $text lexical search — available once corpus is indexed with a text index.
      3. Empty list — if MongoDB is unreachable or collection has no text index.
    """
    if _LANGCHAIN_MONGODB_AVAILABLE:
        return _atlas_hybrid_search(query, top_k)
    return _pymongo_text_search(query, top_k)


def _atlas_hybrid_search(query: str, top_k: int) -> list[dict[str, Any]]:
    """
    TODO: implement after langchain-mongodb is installed and Atlas vector index exists.

    Wire order:
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
      retriever = store.as_retriever(search_type="similarity", search_kwargs={"k": top_k})
      docs = retriever.invoke(query)
      return [_doc_to_hit(d) for d in docs]
    """
    log.warning("_atlas_hybrid_search: langchain-mongodb present but not yet wired")
    return []


def _pymongo_text_search(query: str, top_k: int) -> list[dict[str, Any]]:
    """
    Lexical fallback via pymongo $text operator.

    Requires a text index on foia_precedent — the corpus indexer must have run.
    Returns [] silently if the collection is missing or has no text index.
    """
    coll = _get_collection()
    if coll is None:
        return []
    try:
        cursor = (
            coll.find(
                {"$text": {"$search": query}},
                {"score": {"$meta": "textScore"}, "clause_id": 1, "title": 1, "far_part": 1},
            )
            .sort([("score", {"$meta": "textScore"})])
            .limit(top_k)
        )
        return [_doc_to_hit(doc) for doc in cursor]
    except Exception as exc:
        log.warning("pymongo text search failed (%s); returning no hits", exc)
        return []


def _doc_to_hit(doc: dict[str, Any]) -> dict[str, Any]:
    """Normalize a MongoDB document to the /rag/clause-search hit contract."""
    return {
        "clause_id": doc.get("clause_id", ""),
        "title": doc.get("title", ""),
        "score": float(doc.get("score", 0.0)),
        "far_part": doc.get("far_part", ""),
    }
