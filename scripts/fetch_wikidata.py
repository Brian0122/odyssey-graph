"""
Step 5: Fetch character family relationships from Wikidata (SPARQL).

Reads data/characters_canonical.json (slug + wikidata_id for each canonical
character), queries Wikidata for family relationships (father, mother,
spouse, child, sibling) among those characters only, and writes the result
to data/relationships_wikidata.json for review before importing into MongoDB.

This step does not require any API key or MongoDB connection.
"""

import json
import time
from pathlib import Path

import requests

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CANONICAL_PATH = DATA_DIR / "characters_canonical.json"
OUTPUT_PATH = DATA_DIR / "relationships_wikidata.json"

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
USER_AGENT = "odyssey-graph-demo/0.1 (contact: kailinguy@gmail.com)"

# property -> (relation label for X->Y, reverse relation label for Y->X)
PROPERTIES = {
    "P22": ("CHILD_OF", "FATHER_OF"),   # X has father Y
    "P25": ("CHILD_OF", "MOTHER_OF"),   # X has mother Y
    "P26": ("MARRIED_TO", "MARRIED_TO"),  # X has spouse Y
    "P40": ("PARENT_OF", "CHILD_OF"),   # X has child Y
    "P3373": ("SIBLING_OF", "SIBLING_OF"),  # X has sibling Y
}


def load_canonical():
    with open(CANONICAL_PATH, encoding="utf-8") as f:
        chars = json.load(f)
    # Not every canonical character has a Wikidata item (e.g. philoetius —
    # checked via wbsearchentities, no distinct entity exists) — skip those
    # rather than passing a literal "wd:None" into the SPARQL query below.
    qid_to_slug = {c["wikidata_id"]: c["slug"] for c in chars if c.get("wikidata_id")}
    return chars, qid_to_slug


def fetch_claims(qids):
    values = " ".join(f"wd:{q}" for q in qids)
    props = " ".join(f"wdt:{p}" for p in PROPERTIES)
    query = f"""
    SELECT ?item ?prop ?value WHERE {{
      VALUES ?item {{ {values} }}
      VALUES ?prop {{ {props} }}
      ?item ?prop ?value .
    }}
    """
    resp = requests.get(
        SPARQL_ENDPOINT,
        params={"query": query},
        headers={"Accept": "application/sparql-results+json", "User-Agent": USER_AGENT},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["results"]["bindings"]


def main():
    chars, qid_to_slug = load_canonical()
    qids = list(qid_to_slug.keys())

    print(f"Querying Wikidata for {len(qids)} characters...")
    bindings = fetch_claims(qids)
    time.sleep(0.5)

    edges = []
    seen = set()
    skipped_out_of_scope = []

    for b in bindings:
        item_qid = b["item"]["value"].rsplit("/", 1)[-1]
        prop_id = b["prop"]["value"].rsplit("/", 1)[-1]
        value_qid = b["value"]["value"].rsplit("/", 1)[-1]

        if prop_id not in PROPERTIES:
            continue
        if item_qid not in qid_to_slug:
            continue
        if value_qid not in qid_to_slug:
            skipped_out_of_scope.append((item_qid, prop_id, value_qid))
            continue

        from_slug = qid_to_slug[item_qid]
        to_slug = qid_to_slug[value_qid]
        fwd_label, rev_label = PROPERTIES[prop_id]

        for (a, b_, label) in [(from_slug, to_slug, fwd_label), (to_slug, from_slug, rev_label)]:
            key = (a, b_, label)
            if key in seen or a == b_:
                continue
            seen.add(key)
            edges.append({
                "from_slug": a,
                "to_slug": b_,
                "relation": label,
                "source": "wikidata",
            })

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(edges, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(edges)} edges to {OUTPUT_PATH}")
    print(f"Skipped {len(skipped_out_of_scope)} claims pointing outside the canonical list "
          f"(e.g. non-canonical children like Telegonus).")


if __name__ == "__main__":
    main()
