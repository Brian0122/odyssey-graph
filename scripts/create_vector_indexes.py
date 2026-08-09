"""
Step 6 (execution order) / Vector Search setup: create one Atlas Vector
Search index per node collection (characters, locations, events), using
Automated Embedding (autoEmbed) — Atlas calls Voyage AI itself against
`embedding_source` on write, so the app never computes or stores vectors
directly. Requires the Atlas project's Voyage AI API key to already be
configured (Atlas UI -> Project Settings -> Integrations); this script
can't check or set that.

`relationships` (the edge collection) is intentionally not indexed here —
it's for $graphLookup traversal, not semantic search.

locations/events also get a `filter`-type field on `order`, so a future
spoiler-safe ("新手模式") query can pre-filter `$vectorSearch` results to
`order <= unlocked_progress` directly in the index instead of a slower
post-filter — see docs/schema.md's index planning notes.

Index builds are asynchronous in Atlas; this script only submits the
create requests; check status separately (see check_vector_indexes.py or
the Atlas UI) before relying on them in queries.

Safe to re-run: skips any collection that already has a search index with
the target name.
"""

import os

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.operations import SearchIndexModel

load_dotenv()

MODEL = "voyage-4"

INDEX_SPECS = {
    "characters": {
        "name": "characters_vector_index",
        "fields": [
            {"type": "autoEmbed", "modality": "text", "path": "embedding_source", "model": MODEL},
        ],
    },
    "locations": {
        "name": "locations_vector_index",
        "fields": [
            {"type": "autoEmbed", "modality": "text", "path": "embedding_source", "model": MODEL},
            {"type": "filter", "path": "order"},
        ],
    },
    "events": {
        "name": "events_vector_index",
        "fields": [
            {"type": "autoEmbed", "modality": "text", "path": "embedding_source", "model": MODEL},
            {"type": "filter", "path": "order"},
        ],
    },
}


def main():
    client = MongoClient(os.environ["MONGODB_URI"])
    db = client[os.environ.get("MONGODB_DB_NAME", "odyssey_graph")]

    for coll_name, spec in INDEX_SPECS.items():
        coll = db[coll_name]
        existing = {ix["name"] for ix in coll.list_search_indexes()}
        if spec["name"] in existing:
            print(f"[{coll_name}] index '{spec['name']}' already exists, skipping")
            continue

        model = SearchIndexModel(
            definition={"fields": spec["fields"]},
            name=spec["name"],
            type="vectorSearch",
        )
        result = coll.create_search_index(model)
        print(f"[{coll_name}] submitted index '{result}' (build is async — check status separately)")


if __name__ == "__main__":
    main()
