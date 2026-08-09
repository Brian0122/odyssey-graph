"""Business logic for the adventure map — MongoDB queries only, no
Streamlit/UI code, plain dicts (same discipline as graph_data.py).
"""

from bson import ObjectId

from db import get_db


def fetch_locations(lang: str = "zh") -> list[dict]:
    """Ordered list of locations for the map: id, name, description,
    order, coordinates, book_chapter. Sorted by timeline order.

    `order` here is a clean 1-based position among the ON-MAP locations
    only, NOT the raw MongoDB `order` field — the two can diverge once
    off-map locations exist in between (e.g. Book 5's Ogygia sits at
    DB order 11 between the Books 9-12 stops at 1-10 and the Books
    21-24 capstone at DB order 12). map.py's and the JS map component's
    unlock logic both require a gapless 1,2,3... sequence (clicking
    requires order == unlocked_order + 1) — feeding them the raw DB
    order after an off-map location creates a gap that can never
    satisfy that check, permanently blocking the next stop from
    unlocking. Renumbering by position here keeps that assumption true
    for every caller without having to teach the unlock logic (Python
    and JS both) about on_map filtering.
    """
    db = get_db()
    locations = []
    # on_map defaults True for older docs written before this field existed
    # (Books 9-12) — only explicitly-False locations (Book 5, a narrative
    # bridge with no map stop of its own) are excluded. See docs/schema.md.
    for display_order, loc in enumerate(
        db.locations.find({"on_map": {"$ne": False}}).sort("order", 1), start=1
    ):
        locations.append({
            "id": str(loc["_id"]),
            "name": loc["name"].get(lang) or loc["name"]["en"],
            "description": loc["description"].get(lang) or loc["description"]["en"],
            "order": display_order,
            "book_chapter": loc.get("book_chapter"),
            "image": loc.get("image"),
            "image_credit": loc.get("image_credit"),
            # Recomputed from display_order, not loc["coordinates"] as
            # stored — those were laid out at import time from the raw DB
            # order (see scripts/import_to_mongodb.py's zigzag_coordinates),
            # which would leave a large empty gap on the map where a
            # filtered-out off-map location's slot used to be. Same
            # formula, just fed the renumbered position instead.
            "coordinates": {"x": display_order * 200,
                             "y": 300 + (80 if display_order % 2 == 0 else -80)},
        })
    return locations


def fetch_events_for_location(location_id: str, lang: str = "zh") -> list[dict]:
    """Events that happened at a given location, in timeline order —
    used to populate a location's intro card once it's unlocked.
    """
    db = get_db()
    events = []
    for ev in db.events.find({"location_id": ObjectId(location_id)}).sort("order", 1):
        events.append({
            "id": str(ev["_id"]),
            "name": ev["name"].get(lang) or ev["name"]["en"],
            "description": ev["description"].get(lang) or ev["description"]["en"],
            "source_excerpt": ev.get("source_excerpt"),
        })
    return events


def fetch_characters_for_location(location_id: str, lang: str = "zh") -> list[dict]:
    """Characters who participate in any event at this location — used
    for the "角色初登場卡" (character intro card) on first unlock.
    """
    db = get_db()
    event_ids = [ev["_id"] for ev in db.events.find({"location_id": ObjectId(location_id)}, {"_id": 1})]
    if not event_ids:
        return []
    char_ids = {
        rel["from_id"] for rel in db.relationships.find({
            "to_id": {"$in": event_ids},
            "relation": "PARTICIPATES_IN",
        }, {"from_id": 1})
    }
    characters = []
    for c in db.characters.find({"_id": {"$in": list(char_ids)}}):
        characters.append({
            "id": str(c["_id"]),
            "name": c["name"].get(lang) or c["name"]["en"],
            "description": c["description"].get(lang) or c["description"]["en"],
            "type": c.get("type"),
        })
    return characters
