"""Graph RAG retrieval — combines Atlas Vector Search (semantic recall
across characters/locations/events) with $graphLookup (relationship
traversal) into a single retrieval step, ready to feed an LLM. This is
what a vector-only RAG pipeline can't do: surface indirect relationships
("Telemachus's relation to Poseidon" needs two hops through Odysseus,
which vector similarity alone won't find since their descriptions don't
mention each other).

No Streamlit/UI code, plain dicts — same discipline as graph_data.py.
"""

import time

import voyageai
import voyageai.error
from bson.binary import Binary, BinaryVectorDtype
from dotenv import load_dotenv
from pymongo.errors import OperationFailure

from db import get_db
from graph_data import _graphlookup_direct_edges
from secrets_util import get_secret

load_dotenv()

VECTOR_INDEXES = {
    "characters": "characters_vector_index",
    "locations": "locations_vector_index",
    "events": "events_vector_index",
}
COLLECTION_NODE_TYPE = {
    "characters": "character",
    "locations": "location",
    "events": "event",
}

# Must match scripts/create_vector_indexes.py's index definitions exactly
# (model + dimensions + quantization) — a mismatched query vector either
# errors outright or silently returns nonsense similarity scores. Checked
# directly against the live index definition (list_search_indexes()),
# not assumed: numDimensions=1024, quantization="scalar" (-> queryVector
# must be int8, not float32, or Atlas rejects it).
EMBED_MODEL = "voyage-4"
EMBED_DIMENSION = 1024

_RATE_LIMIT_RETRIES = 3
_RATE_LIMIT_BACKOFF_SECONDS = 1.5

_voyage_client = voyageai.Client(api_key=get_secret("VOYAGE_API_KEY"))


def _embed_query(text: str) -> Binary:
    """Embed once ourselves (input_type="query", matching how Atlas
    Automated Embedding treats $vectorSearch's `query` text) and reuse the
    same vector across all three collections' $vectorSearch calls via
    `queryVector`, instead of letting Atlas auto-embed the same text three
    times over. Same total information, one Voyage AI call instead of
    three — cuts query-time Voyage traffic (and rate-limit exposure) by
    two thirds without touching how documents get embedded on write.
    """
    for attempt in range(_RATE_LIMIT_RETRIES):
        try:
            result = _voyage_client.embed(
                texts=[text],
                model=EMBED_MODEL,
                input_type="query",
                output_dimension=EMBED_DIMENSION,
                output_dtype="int8",
            )
            return Binary.from_vector(result.embeddings[0], BinaryVectorDtype.INT8)
        except voyageai.error.RateLimitError:
            if attempt == _RATE_LIMIT_RETRIES - 1:
                raise
            time.sleep(_RATE_LIMIT_BACKOFF_SECONDS * (attempt + 1))


def _aggregate_with_retry(coll, pipeline):
    """Belt-and-suspenders for any remaining transient Atlas-side errors
    on the $vectorSearch call itself (the query-embedding rate limit is
    now avoided upstream by _embed_query's single shared call, but this
    still guards against other momentary blips)."""
    for attempt in range(_RATE_LIMIT_RETRIES):
        try:
            return list(coll.aggregate(pipeline))
        except OperationFailure as e:
            is_last = attempt == _RATE_LIMIT_RETRIES - 1
            if "rate limit" not in str(e).lower() or is_last:
                raise
            time.sleep(_RATE_LIMIT_BACKOFF_SECONDS * (attempt + 1))


def vector_search(query_vector: Binary, collection: str, lang: str = "en",
                   limit: int = 3, num_candidates: int = 60) -> list[dict]:
    """Semantic search a single node collection using a pre-computed query
    vector (see _embed_query) against its Atlas Vector Search index.
    """
    db = get_db()
    pipeline = [
        {
            "$vectorSearch": {
                "index": VECTOR_INDEXES[collection],
                "path": "embedding_source",
                "queryVector": query_vector,
                "numCandidates": num_candidates,
                "limit": limit,
            }
        },
        {
            "$project": {
                "name": 1,
                "description": 1,
                "source_excerpt": 1,
                "score": {"$meta": "vectorSearchScore"},
            }
        },
    ]
    results = []
    for doc in _aggregate_with_retry(db[collection], pipeline):
        results.append({
            "id": str(doc["_id"]),
            "node_type": COLLECTION_NODE_TYPE[collection],
            "name": doc["name"].get(lang) or doc["name"]["en"],
            "description": doc["description"].get(lang) or doc["description"]["en"],
            "source_excerpt": doc.get("source_excerpt"),  # events only
            "score": doc["score"],
        })
    return results


def vector_only_search(query: str, lang: str = "en", per_collection_limit: int = 3) -> dict:
    """Semantic search alone, no $graphLookup expansion — the deliberately
    weaker retrieval used by the split-screen "純向量 RAG" side of the
    comparison tab, to make the contrast with graph_rag_retrieve() honest
    and visible rather than asserted.

    Returns {"matches": [...]} — same match shape as graph_rag_retrieve,
    just without any relationships/citations, since there's no graph
    traversal here to produce them.
    """
    query_vector = _embed_query(query)
    matches = []
    for coll in ("characters", "locations", "events"):
        matches.extend(vector_search(query_vector, coll, lang=lang, limit=per_collection_limit))
    matches.sort(key=lambda m: m["score"], reverse=True)
    return {"matches": matches}


def graph_rag_retrieve(query: str, lang: str = "en", per_collection_limit: int = 3,
                        expand_depth: int = 2) -> dict:
    """Full Graph RAG retrieval for one natural-language query.

    1. Embed the query once, then vector search all three node
       collections for semantically relevant hits ("matches").
    2. $graphLookup outward from every match to collect their direct
       relationships, then (if expand_depth >= 2) one more hop from any
       event/location neighbor reached — characters don't act as
       pass-through hubs, same rule as graph_data.py's focus mode, so a
       popular character like Odysseus doesn't flood unrelated context
       just because he's tangentially connected.
    3. Package matches + deduped relationship edges + citable source
       excerpts for an LLM to answer from.

    Returns {"matches": [...], "relationships": [...], "citations": [...]}
    """
    db = get_db()

    query_vector = _embed_query(query)
    matches = []
    for coll in ("characters", "locations", "events"):
        matches.extend(vector_search(query_vector, coll, lang=lang, limit=per_collection_limit))
    matches.sort(key=lambda m: m["score"], reverse=True)

    seed_ids = {m["id"] for m in matches}
    all_raw_edges = []
    for nid in seed_ids:
        all_raw_edges.extend(_graphlookup_direct_edges(db, nid))

    if expand_depth >= 2:
        # from_type/to_type are already stored on the edge (see
        # docs/schema.md) — no extra lookup needed to apply the
        # "characters are leaves" rule.
        expandable = set()
        for e in all_raw_edges:
            fid, tid = str(e["from_id"]), str(e["to_id"])
            if fid not in seed_ids and e.get("from_type") != "character":
                expandable.add(fid)
            if tid not in seed_ids and e.get("to_type") != "character":
                expandable.add(tid)
        for nid in expandable:
            all_raw_edges.extend(_graphlookup_direct_edges(db, nid))

    seen = set()
    relationships = []
    for raw in all_raw_edges:
        key = (str(raw["from_id"]), str(raw["to_id"]), raw["relation"])
        if key in seen:
            continue
        seen.add(key)
        desc = raw.get("description")
        from_name = raw.get("from_name") or {}
        to_name = raw.get("to_name") or {}
        relationships.append({
            "source": str(raw["from_id"]),
            "source_name": from_name.get(lang) or from_name.get("en"),
            "target": str(raw["to_id"]),
            "target_name": to_name.get(lang) or to_name.get("en"),
            "relation": raw["relation"],
            "description": (desc.get(lang) or desc.get("en")) if desc else None,
        })

    citations = [
        {"id": m["id"], "name": m["name"], "source_excerpt": m["source_excerpt"]}
        for m in matches if m.get("source_excerpt")
    ]

    return {"matches": matches, "relationships": relationships, "citations": citations}
