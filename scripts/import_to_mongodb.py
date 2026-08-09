"""
Step 7: Import characters, locations, events, and relationships into
MongoDB Atlas.

Merges four data sources:
- data/characters_canonical.json + data/characters_enriched.json -> `characters`
  (upsert by `slug`, the stable key shared across the Wikidata and LLM pipelines)
- EXTRACTION_BATCHES (below) -> `locations`, `events`, and most of `relationships`.
  Each batch is a separate scripts/extract_books.py run's output (Books 9-12,
  Book 5, Books 21-24 — see that script) — merged here rather than requiring
  one giant extraction call, so expanding the dataset never touches the
  original, already-demo-verified Books 9-12 output. Each batch's temp_ids
  ("loc_1", "event_1", ...) are batch-local by construction (every batch
  independently starts counting from 1) — merge_batches() namespaces them
  with a batch prefix before combining, so "loc_1" from two different
  batches can't collide.
- data/relationships_wikidata.json -> the rest of `relationships` (family ties)

Locations/events don't have real MongoDB _ids until inserted, so the
(namespaced) temp_ids are resolved to real ObjectIds after insertion, before
relationship edges are written.

`relationships` also gets PARTICIPATES_IN edges generated programmatically
from each event's `character_slugs` (not stored as a relationship edge by
the LLM itself, to avoid inconsistent coverage — see extract_books.py).

Safe to re-run: `locations`/`events`/`relationships` are fully owned by this
pipeline and are cleared before each import; `characters` are upserted by
slug so re-running only updates existing docs.
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# (file name, whether this batch's locations belong on the adventure map).
# Book 5 and Books 21-24 are both real MongoDB data (queryable everywhere —
# knowledge graph, AI 問答, 對照展示) but only the Books 21-24 capstone
# location is meant to appear on the adventure map — see CLAUDE.md's 目前進度
# note on this batch for why (Book 5 is a narrative bridge with no map
# stop of its own; app/map_data.py's fetch_locations() filters on on_map).
EXTRACTION_BATCHES = [
    ("extraction_gemini.json", True),
    ("extraction_gemini_book5.json", False),
    ("extraction_gemini_books21-24.json", True),
]


def load_json(name):
    with open(DATA_DIR / name, encoding="utf-8") as f:
        return json.load(f)


def merge_batches(batches: list[tuple[str, bool]]) -> dict:
    """Combine multiple extract_books.py outputs into one extraction-shaped
    dict, namespacing every temp_id by batch index first so same-named
    temp_ids from different batches ("loc_1" in both Book 5 and Books
    21-24, say) can't collide. Also tags each location with on_map and
    drops relationship edges that exactly duplicate one from an earlier
    batch (e.g. Book 5 and Books 9-12 both independently produce a
    poseidon ANTAGONIST_OF odysseus edge) — same (from, to, relation)
    triple wins once, first batch processed takes priority.
    """
    merged = {"locations": [], "events": [], "relationships": []}
    seen_relationship_keys = set()

    for batch_idx, (filename, on_map) in enumerate(batches):
        extraction = load_json(filename)
        prefix = f"b{batch_idx}_"

        def ns(temp_id: str) -> str:
            return prefix + temp_id

        for loc in extraction["locations"]:
            loc = {**loc, "temp_id": ns(loc["temp_id"]), "on_map": on_map}
            merged["locations"].append(loc)

        for ev in extraction["events"]:
            ev = {
                **ev,
                "temp_id": ns(ev["temp_id"]),
                "location_temp_id": ns(ev["location_temp_id"]),
            }
            merged["events"].append(ev)

        for rel in extraction["relationships"]:
            from_ref = ns(rel["from_ref"]) if rel["from_type"] != "character" else rel["from_ref"]
            to_ref = ns(rel["to_ref"]) if rel["to_type"] != "character" else rel["to_ref"]
            key = (from_ref, to_ref, rel["relation"])
            if key in seen_relationship_keys:
                continue
            seen_relationship_keys.add(key)
            merged["relationships"].append({**rel, "from_ref": from_ref, "to_ref": to_ref})

    return merged


def import_characters(db, canonical, enriched, extraction):
    enriched_by_slug = {e["slug"]: e for e in enriched}

    # source provenance: every canonical character has a wikidata_id (Step 5);
    # mark llm_extracted too if they appear in any extracted event/relationship
    # (across all merged batches, not just Books 9-12)
    narrative_slugs = set()
    for ev in extraction["events"]:
        narrative_slugs.update(ev["character_slugs"])
    for rel in extraction["relationships"]:
        for ref, typ in [(rel["from_ref"], rel["from_type"]), (rel["to_ref"], rel["to_type"])]:
            if typ == "character":
                narrative_slugs.add(ref)

    slug_to_id = {}
    char_id_to_name = {}
    for c in canonical:
        enr = enriched_by_slug.get(c["slug"], {})
        source = ["wikidata"]
        if c["slug"] in narrative_slugs:
            source.append("llm_extracted")

        description_en = enr.get("description_en", "")
        name = {"en": c["name_en"], "zh": enr.get("name_zh", "")}
        doc = {
            "slug": c["slug"],
            "name": name,
            "aliases": c.get("aliases", []),
            "type": c["type"],
            "description": {"en": description_en, "zh": enr.get("description_zh", "")},
            "embedding_source": description_en,
            "wikidata_id": c.get("wikidata_id"),
            "source": source,
        }
        result = db.characters.update_one(
            {"slug": c["slug"]}, {"$set": doc}, upsert=True
        )
        char_id = result.upserted_id or db.characters.find_one({"slug": c["slug"]})["_id"]
        slug_to_id[c["slug"]] = char_id
        char_id_to_name[char_id] = name

    print(f"Upserted {len(slug_to_id)} characters")
    return slug_to_id, char_id_to_name


def zigzag_coordinates(order: int) -> dict:
    return {"x": order * 200, "y": 300 + (80 if order % 2 == 0 else -80)}


# Public-domain artwork depicting each location's Odyssey episode, one per
# `order` — sourced from Wikimedia Commons (see app/assets/locations/) and
# verified individually for licensing before download. Not LLM-extracted
# content, so it's kept out of extraction_gemini.json and mapped here at
# import time instead.
_FLAXMAN = "John Flaxman, Compositions from the Odyssey of Homer (engraved early 19th c.)"
LOCATION_IMAGES = {
    1: ("locations/01-ismaros.jpg",
        "Theodoor van Thulden, Odysseus vecht met de Kikonen (1632–33), Rijksmuseum"),
    2: ("locations/02-lotus-eaters.jpg",
        "Theodoor van Thulden, Odysseus in het land van de lotuseters (1632–33), Rijksmuseum"),
    3: ("locations/03-cyclops.png", _FLAXMAN),
    4: ("locations/04-aeolia.jpg",
        "Isaac Moillon, Éole donnant les vents à Ulysse (17th c.), Musée de Tessé"),
    5: ("locations/05-laestrygonians.png", _FLAXMAN),
    6: ("locations/06-circe.jpg",
        "Willy Pogány, in Padraic Colum's The Adventures of Odysseus and the Tale of Troy (1918)"),
    7: ("locations/07-underworld.png", _FLAXMAN),
    8: ("locations/08-sirens.jpg",
        "Willy Pogány, in Padraic Colum's The Adventures of Odysseus and the Tale of Troy (1918)"),
    9: ("locations/09-scylla.png", _FLAXMAN),
    10: ("locations/10-thrinacia.png", _FLAXMAN),
}


def import_locations(db, extraction):
    db.locations.delete_many({})
    temp_to_id = {}
    docs = []
    for loc in extraction["locations"]:
        image, image_credit = LOCATION_IMAGES.get(loc["order"], (None, None))
        docs.append({
            "temp_id": loc["temp_id"],
            "name": loc["name"],
            "description": loc["description"],
            "embedding_source": loc["description"]["en"],
            "order": loc["order"],
            "book_chapter": loc["book_chapter"],
            "coordinates": zigzag_coordinates(loc["order"]),
            "image": image,
            "image_credit": image_credit,
            "on_map": loc.get("on_map", True),
            "source": "llm_extracted",
        })
    result = db.locations.insert_many(docs)
    for doc, _id in zip(docs, result.inserted_ids):
        temp_to_id[doc["temp_id"]] = _id
        db.locations.update_one({"_id": _id}, {"$unset": {"temp_id": ""}})
    print(f"Inserted {len(temp_to_id)} locations")
    return temp_to_id


def import_events(db, extraction, loc_temp_to_id):
    db.events.delete_many({})
    temp_to_id = {}
    temp_to_doc = {ev["temp_id"]: ev for ev in extraction["events"]}
    docs = []
    for ev in extraction["events"]:
        docs.append({
            "temp_id": ev["temp_id"],
            "name": ev["name"],
            "description": ev["description"],
            "embedding_source": f"{ev['description']['en']} {ev['source_excerpt']}",
            "location_id": loc_temp_to_id[ev["location_temp_id"]],
            "order": ev["order"],
            "book_chapter": ev["book_chapter"],
            "source_excerpt": ev["source_excerpt"],
            "source": "llm_extracted",
        })
    result = db.events.insert_many(docs)
    for doc, _id in zip(docs, result.inserted_ids):
        temp_to_id[doc["temp_id"]] = _id
        db.events.update_one({"_id": _id}, {"$unset": {"temp_id": ""}})
    print(f"Inserted {len(temp_to_id)} events")
    return temp_to_id, temp_to_doc


def resolve_ref(ref, ref_type, slug_to_char_id, loc_temp_to_id, event_temp_to_id,
                 char_by_id, loc_by_temp, event_by_temp):
    if ref_type == "character":
        return slug_to_char_id[ref], char_by_id[slug_to_char_id[ref]]
    if ref_type == "location":
        return loc_temp_to_id[ref], loc_by_temp[ref]["name"]
    if ref_type == "event":
        return event_temp_to_id[ref], event_by_temp[ref]["name"]
    raise ValueError(f"unknown ref_type {ref_type}")


def infer_order_for_character_pair(from_slug, to_slug, extraction):
    matches = [
        ev["order"] for ev in extraction["events"]
        if from_slug in ev["character_slugs"] and to_slug in ev["character_slugs"]
    ]
    return min(matches) if matches else None


def import_relationships(db, extraction, wikidata_rels, slug_to_char_id,
                          loc_temp_to_id, event_temp_to_id, char_by_id):
    db.relationships.delete_many({})

    loc_by_temp = {loc["temp_id"]: loc for loc in extraction["locations"]}
    event_by_temp = {ev["temp_id"]: ev for ev in extraction["events"]}

    docs = []

    # 1. Wikidata family relationships (character <-> character only)
    for rel in wikidata_rels:
        from_id = slug_to_char_id[rel["from_slug"]]
        to_id = slug_to_char_id[rel["to_slug"]]
        docs.append({
            "from_id": from_id,
            "from_type": "character",
            "from_name": char_by_id[from_id],
            "to_id": to_id,
            "to_type": "character",
            "to_name": char_by_id[to_id],
            "relation": rel["relation"],
            "description": None,
            "order": None,
            "source": "wikidata",
        })

    # 2. LLM-extracted narrative relationships
    for rel in extraction["relationships"]:
        from_id, from_name = resolve_ref(
            rel["from_ref"], rel["from_type"], slug_to_char_id, loc_temp_to_id,
            event_temp_to_id, char_by_id, loc_by_temp, event_by_temp,
        )
        to_id, to_name = resolve_ref(
            rel["to_ref"], rel["to_type"], slug_to_char_id, loc_temp_to_id,
            event_temp_to_id, char_by_id, loc_by_temp, event_by_temp,
        )
        order = None
        if rel["from_type"] == "event":
            order = event_by_temp[rel["from_ref"]]["order"]
        elif rel["to_type"] == "event":
            order = event_by_temp[rel["to_ref"]]["order"]
        elif rel["from_type"] == "character" and rel["to_type"] == "character":
            order = infer_order_for_character_pair(rel["from_ref"], rel["to_ref"], extraction)

        docs.append({
            "from_id": from_id,
            "from_type": rel["from_type"],
            "from_name": from_name,
            "to_id": to_id,
            "to_type": rel["to_type"],
            "to_name": to_name,
            "relation": rel["relation"],
            "description": rel.get("description"),
            "order": order,
            "source": "llm_extracted",
        })

    # 3. Programmatically generated PARTICIPATES_IN edges from character_slugs.
    # description = the event's own description, so hovering the edge shows
    # what actually happened instead of just repeating the "參與" label.
    for ev in extraction["events"]:
        event_id = event_temp_to_id[ev["temp_id"]]
        for slug in ev["character_slugs"]:
            char_id = slug_to_char_id[slug]
            docs.append({
                "from_id": char_id,
                "from_type": "character",
                "from_name": char_by_id[char_id],
                "to_id": event_id,
                "to_type": "event",
                "to_name": ev["name"],
                "relation": "PARTICIPATES_IN",
                "description": ev["description"],
                "order": ev["order"],
                "source": "llm_extracted",
            })

    # 4. Programmatically generated LOCATED_AT edges from event.location_id.
    # Not redundant with the field: this is what lets $graphLookup traverse
    # through locations (e.g. "what else happened where X happened") —
    # without a stored edge, location nodes are unreachable by graph
    # traversal even though the field captures the same fact for direct
    # lookups. See docs/schema.md.
    for ev in extraction["events"]:
        event_id = event_temp_to_id[ev["temp_id"]]
        loc_id = loc_temp_to_id[ev["location_temp_id"]]
        loc_doc = loc_by_temp[ev["location_temp_id"]]
        docs.append({
            "from_id": event_id,
            "from_type": "event",
            "from_name": ev["name"],
            "to_id": loc_id,
            "to_type": "location",
            "to_name": loc_doc["name"],
            "relation": "LOCATED_AT",
            "description": loc_doc["description"],
            "order": ev["order"],
            "source": "llm_extracted",
        })

    db.relationships.insert_many(docs)
    print(f"Inserted {len(docs)} relationships "
          f"({len(wikidata_rels)} wikidata + "
          f"{len(extraction['relationships'])} llm narrative + "
          f"{sum(len(ev['character_slugs']) for ev in extraction['events'])} participates_in + "
          f"{len(extraction['events'])} located_at)")


def main():
    uri = os.environ["MONGODB_URI"]
    db_name = os.environ.get("MONGODB_DB_NAME", "odyssey_graph")
    client = MongoClient(uri)
    db = client[db_name]

    canonical = load_json("characters_canonical.json")
    enriched = load_json("characters_enriched.json")
    extraction = merge_batches(EXTRACTION_BATCHES)
    wikidata_rels = load_json("relationships_wikidata.json")

    slug_to_char_id, char_id_to_name = import_characters(db, canonical, enriched, extraction)
    loc_temp_to_id = import_locations(db, extraction)
    event_temp_to_id, _ = import_events(db, extraction, loc_temp_to_id)
    import_relationships(
        db, extraction, wikidata_rels, slug_to_char_id, loc_temp_to_id,
        event_temp_to_id, char_id_to_name,
    )

    print("\nDone. Collection counts:")
    for coll in ["characters", "locations", "events", "relationships"]:
        print(f"  {coll}: {db[coll].count_documents({})}")


if __name__ == "__main__":
    main()
