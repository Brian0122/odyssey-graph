"""Business logic for the knowledge graph view — MongoDB queries only, no
Streamlit/UI code here, and no framework-specific types. Returns plain
dicts so the same function can feed streamlit-agraph now and a React/
Cytoscape.js component later without changing this module.
"""

from db import get_db

# Shared visual vocabulary for any streamlit-agraph rendering of these node
# types (app/views/graph.py, app/views/compare.py) — kept in one place so
# the knowledge graph tab and the Graph RAG comparison tab's subgraph
# viz can't silently drift apart.
#
# Colors are the first 3 slots of the validated dataviz palette, DARK-mode
# variants (the app runs on a dark theme — see .streamlit/config.toml).
# These are the only slots that clear the all-pairs CVD/contrast floor.
# See dataviz skill references/palette.md.
NODE_TYPE_COLOR = {
    "character": "#3987e5",  # blue (dark)
    "location": "#199e70",   # aqua (dark)
    "event": "#d95926",      # orange (dark)
}
# vis-network's default label font is dark (meant for light backgrounds) —
# on our dark theme it was reading as low-contrast/unclear. Set explicitly.
LABEL_FONT_COLOR = "#f0e6c8"
NODE_TYPE_SHAPE = {
    "character": "dot",
    "location": "square",
    "event": "triangle",
}
# Unicode glyphs matching each type's actual NODE_TYPE_SHAPE above, so a
# legend's symbol corresponds to what's really drawn on the graph instead
# of showing a circle for every type regardless of its real shape.
NODE_TYPE_GLYPH = {
    "character": "●",
    "location": "■",
    "event": "▲",
}


def fetch_graph_data(lang: str = "zh") -> dict:
    """Returns {"nodes": [...], "edges": [...]} for the full knowledge graph.

    Each node: {id, label, node_type, sub_type}
        node_type: "character" | "location" | "event"
        sub_type: character.type (mortal/god/monster/creature) for characters, else None
    Each edge: {source, target, relation}
    """
    db = get_db()

    nodes = []
    for c in db.characters.find():
        nodes.append({
            "id": str(c["_id"]),
            "label": c["name"].get(lang) or c["name"]["en"],
            "node_type": "character",
            "sub_type": c.get("type"),
            "description": c["description"].get(lang) or c["description"]["en"],
        })
    for loc in db.locations.find():
        nodes.append({
            "id": str(loc["_id"]),
            "label": loc["name"].get(lang) or loc["name"]["en"],
            "node_type": "location",
            "sub_type": None,
            "description": loc["description"].get(lang) or loc["description"]["en"],
        })
    for ev in db.events.find():
        nodes.append({
            "id": str(ev["_id"]),
            "label": ev["name"].get(lang) or ev["name"]["en"],
            "node_type": "event",
            "sub_type": None,
            "description": ev["description"].get(lang) or ev["description"]["en"],
        })

    edges = []
    for rel in db.relationships.find():
        desc = rel.get("description")
        edges.append({
            "source": str(rel["from_id"]),
            "target": str(rel["to_id"]),
            "relation": rel["relation"],
            "description": desc.get(lang) or desc.get("en") if desc else None,
        })

    return {"nodes": nodes, "edges": edges}


def filter_graph(data: dict, node_types: set, exclude_relations: set,
                  focus_node_id: str | None = None, focus_depth: int = 2) -> dict:
    """Pure filtering logic — no DB access, no Streamlit. Takes the full
    graph and returns a subset for display.

    - node_types: which node_type values to keep (e.g. {"character"}) —
      applied even in focus mode, so a neighbor whose type isn't selected
      stays hidden
    - exclude_relations: relation labels to drop (e.g. {"PARTICIPATES_IN"})
    - focus_node_id: if set, keep only this node and nodes reachable within
      focus_depth hops (of the selected types) — e.g. character -> event
      -> location is 2 hops, since characters and locations are never
      directly connected in this data. Only event/location nodes act as
      pass-through stepping stones for a further hop — a character reached
      at hop 1 is included but is NOT used to jump further (otherwise
      focusing on a character with many connections, like Odysseus, would
      flood a 2-hop neighbor's view with everything Odysseus touches,
      unrelated to the actual focus node).
    """
    edges = [e for e in data["edges"] if e["relation"] not in exclude_relations]

    if focus_node_id:
        allowed_ids = {n["id"] for n in data["nodes"] if n["node_type"] in node_types}
        allowed_ids.add(focus_node_id)  # always show the focus node itself
        node_type_by_id = {n["id"]: n["node_type"] for n in data["nodes"]}

        reached_ids = {focus_node_id}
        frontier = {focus_node_id}
        for _ in range(focus_depth):
            next_frontier = set()
            for e in edges:
                if e["source"] in frontier and e["target"] in allowed_ids \
                        and e["target"] not in reached_ids:
                    next_frontier.add(e["target"])
                elif e["target"] in frontier and e["source"] in allowed_ids \
                        and e["source"] not in reached_ids:
                    next_frontier.add(e["source"])
            if not next_frontier:
                break
            reached_ids |= next_frontier
            # Characters are leaves for the purpose of further expansion —
            # only events/locations carry the search onward.
            frontier = {nid for nid in next_frontier if node_type_by_id.get(nid) != "character"}

        edges = [e for e in edges
                 if e["source"] in reached_ids and e["target"] in reached_ids]
        nodes = [n for n in data["nodes"] if n["id"] in reached_ids]
        return {"nodes": nodes, "edges": edges}

    nodes = [n for n in data["nodes"] if n["node_type"] in node_types]
    node_ids = {n["id"] for n in nodes}
    edges = [e for e in edges if e["source"] in node_ids and e["target"] in node_ids]
    return {"nodes": nodes, "edges": edges}


# Family relations are stored bidirectionally in MongoDB on purpose (so
# $graphLookup can traverse from either end — see fetch_wikidata.py), but
# showing both directions as separate edges on the same node pair just
# looks like a tangle. This is a DISPLAY-only dedup: pick the single
# clearest edge per node pair, in preference order. The DB is untouched.
_FAMILY_RELATIONS = {"FATHER_OF", "MOTHER_OF", "PARENT_OF", "CHILD_OF",
                      "MARRIED_TO", "SIBLING_OF"}
_FAMILY_PREFERENCE = ["FATHER_OF", "MOTHER_OF", "PARENT_OF", "MARRIED_TO",
                       "SIBLING_OF", "CHILD_OF"]


def dedupe_family_edges_for_display(edges: list) -> list:
    by_pair = {}
    other_edges = []
    for e in edges:
        if e["relation"] not in _FAMILY_RELATIONS:
            other_edges.append(e)
            continue
        pair_key = frozenset({e["source"], e["target"]})
        by_pair.setdefault(pair_key, []).append(e)

    deduped = []
    for pair_edges in by_pair.values():
        best = min(
            pair_edges,
            key=lambda e: _FAMILY_PREFERENCE.index(e["relation"]),
        )
        deduped.append(best)

    return other_edges + deduped


# Structural edges generated programmatically at import time (see
# scripts/import_to_mongodb.py) rather than representing a narrative
# relationship — not interesting to surface in a "relationship path"
# citation display.
_STRUCTURAL_RELATIONS = {"PARTICIPATES_IN", "LOCATED_AT"}


def filter_relevant_relationships(relationships: list, answer_text: str) -> list:
    """Narrow a (possibly large — a 2-hop $graphLookup expansion can
    return 50+ edges) relationship list down to just the ones an LLM
    answer actually appears to be built on, for a citation/path display
    that's legible instead of overwhelming. Used by both app/views/qa.py
    (inline citations) and app/views/compare.py (Graph RAG subgraph).

    Heuristic: keep an edge only if BOTH endpoint names are substrings of
    the answer text — in practice this reliably narrows a large expansion
    down to the handful of edges the answer is actually about, without
    needing the model to self-report which edges it used.
    """
    relevant = []
    seen = set()
    for r in relationships:
        key = (r["source"], r["target"], r["relation"])
        if key in seen or r["relation"] in _STRUCTURAL_RELATIONS:
            continue
        if not r["source_name"] or not r["target_name"]:
            continue
        if r["source_name"] in answer_text and r["target_name"] in answer_text:
            seen.add(key)
            relevant.append(r)
    return dedupe_family_edges_for_display(relevant)


def _graphlookup_direct_edges(db, node_id: str) -> list:
    """One hop, both directions, via two $graphLookup calls (maxDepth=0 —
    i.e. just the direct matches). Two calls because a relationship edge
    is directional (from_id -> to_id) but we want neighbors regardless of
    which side node_id is on; $graphLookup itself can only follow one
    direction per call. $graphLookup needs a starting document, so try
    each node collection until one has this _id.
    """
    from bson import ObjectId
    oid = ObjectId(node_id)
    pipeline = [
        {"$match": {"_id": oid}},
        {"$graphLookup": {
            "from": "relationships", "startWith": "$_id",
            "connectFromField": "to_id", "connectToField": "from_id",
            "as": "outgoing", "maxDepth": 0,
        }},
        {"$graphLookup": {
            "from": "relationships", "startWith": "$_id",
            "connectFromField": "from_id", "connectToField": "to_id",
            "as": "incoming", "maxDepth": 0,
        }},
    ]
    for coll_name in ["characters", "locations", "events"]:
        result = list(db[coll_name].aggregate(pipeline))
        if result:
            return result[0]["outgoing"] + result[0]["incoming"]
    return []


def graphlookup_ego_network(all_nodes: list, focus_node_id: str, node_types: set,
                             exclude_relations: set, focus_depth: int = 2,
                             lang: str = "zh") -> dict:
    """Same ego-network semantics as filter_graph's focus mode, but the
    traversal runs as live MongoDB $graphLookup calls — one per hop —
    instead of a Python BFS over an already-fetched edge list. Characters
    remain "leaves" (only event/location hop-1 results are expanded to
    hop 2), matching filter_graph's rule, since $graphLookup itself has
    no way to vary its restriction by depth in a single call.

    `all_nodes` is the already-fetched node list from fetch_graph_data()
    (used only to look up node_type by id — avoids a redundant full
    collection scan just for that).
    """
    db = get_db()
    node_type_by_id = {n["id"]: n["node_type"] for n in all_nodes}
    node_by_id = {n["id"]: n for n in all_nodes}

    def to_edge_dict(raw):
        desc = raw.get("description")
        return {
            "source": str(raw["from_id"]),
            "target": str(raw["to_id"]),
            "relation": raw["relation"],
            "description": (desc.get(lang) or desc.get("en")) if desc else None,
        }

    all_raw_edges = list(_graphlookup_direct_edges(db, focus_node_id))

    if focus_depth >= 2:
        hop1_neighbor_ids = set()
        for e in all_raw_edges:
            hop1_neighbor_ids.add(str(e["from_id"]))
            hop1_neighbor_ids.add(str(e["to_id"]))
        hop1_neighbor_ids.discard(focus_node_id)
        # Only expand further from event/location neighbors — characters
        # don't act as pass-through stepping stones (see filter_graph).
        expandable = [nid for nid in hop1_neighbor_ids
                      if node_type_by_id.get(nid) != "character"]
        for nid in expandable:
            all_raw_edges.extend(_graphlookup_direct_edges(db, nid))

    seen = set()
    edges = []
    for raw in all_raw_edges:
        if raw["relation"] in exclude_relations:
            continue
        key = (str(raw["from_id"]), str(raw["to_id"]), raw["relation"])
        if key in seen:
            continue
        seen.add(key)
        edges.append(to_edge_dict(raw))

    allowed_ids = {nid for nid, t in node_type_by_id.items() if t in node_types}
    allowed_ids.add(focus_node_id)
    edges = [e for e in edges if e["source"] in allowed_ids and e["target"] in allowed_ids]

    reached_ids = {focus_node_id}
    for e in edges:
        reached_ids.add(e["source"])
        reached_ids.add(e["target"])

    nodes = [node_by_id[nid] for nid in reached_ids if nid in node_by_id]
    return {"nodes": nodes, "edges": edges}
