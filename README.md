# Odyssey-Graph

An interactive knowledge graph of Homer's *Odyssey*, built as a demo of **MongoDB Atlas** doing Vector Search and graph traversal (`$graphLookup`) natively, in a single database — no separate graph database required.

Covers the most iconic stretch of the epic: Odysseus's wanderings (Books 9-12 — the Cyclops, Aeolus's winds, Circe, the Underworld, the Sirens, Scylla & Charybdis), the journey home from Calypso's island (Book 5), and the return to Ithaca (Books 21-24 — the contest of the bow, the slaughter of the suitors, and the reunion with Penelope and Laertes).

## Features

- 🗺️ **Adventure Map** — fog-of-war unlock mechanic, follow Odysseus's route stop by stop, with location and character intro cards
- 🕸️ **Knowledge Graph** — force-directed visualization of character/location/event relationships, with live `$graphLookup` traversal
- 💬 **Graph RAG Q&A** — ask any question in natural language; answers cite the actual relationship path and source text, not a black box
- ⚖️ **Graph RAG vs. Vector RAG Comparison** — the same question run through both pipelines side by side, showing what only multi-hop graph traversal can answer (e.g. "What's the relationship between Telemachus and Poseidon?" — two hops through Odysseus — vector search alone can't find it)

The UI is bilingual (繁體中文 / English), switchable from the sidebar.

## Why MongoDB Atlas

Most applications that need "relationships" reach for a separate specialized graph database. This demo argues that for a graph of this scale (~130 nodes, a few hundred edges) — which covers a lot of real applications — you don't need to: one Atlas cluster can do both semantic search and graph traversal, which means one system to run instead of two, and no data-sync pipeline between them.

- **`$graphLookup`** — recursive graph traversal for character/location/event relationships, in the same query language as everything else
- **Atlas Vector Search** — semantic search across characters, locations, and events
- **Atlas Automated Embedding + Voyage AI** — vectors are generated automatically when documents are written; no separate embedding pipeline to maintain

## Tech Stack

MongoDB Atlas (Vector Search + `$graphLookup` + Automated Embedding) · Voyage AI · Google Gemini (function calling) · Streamlit · Python

## Architecture

- **Write path**: `characters`/`locations`/`events` use Atlas Automated Embedding — writing a document automatically triggers Voyage AI to embed it, no application code involved.
- **Query path**: the query text is embedded once (via Voyage AI directly, matching the index's model/dimensions/quantization), and that same vector is reused across all three collections' `$vectorSearch` calls — cuts query-time embedding calls from 3 per question down to 1.
- **Graph RAG retrieval** (`app/rag.py`): vector search finds semantically relevant seed nodes, then `$graphLookup` expands their relationships outward (characters don't act as pass-through hubs, so a well-connected character doesn't flood unrelated context). The LLM answers from the expanded subgraph, and the UI independently re-derives which edges the answer actually used (substring-matching the answer text against candidate edges) for the citation panel — trust doesn't depend on the model self-reporting its sources.

See `CLAUDE.md` for the full build log, including every design decision, dead end, and bug fix along the way.

## Setup

```bash
conda create -n odyssey-graph python=3.11
conda activate odyssey-graph
pip install -r requirements.txt

cp .env.example .env
# fill in MONGODB_URI, GEMINI_API_KEY, VOYAGE_API_KEY (see .env.example for details)

# One-time Atlas setup: create the Vector Search indexes, then import the data
# (already-generated data files are committed under data/ — no need to re-run
# the Wikidata/LLM extraction scripts unless you're changing the dataset)
python scripts/create_vector_indexes.py
python scripts/import_to_mongodb.py

streamlit run app/main.py
```

## Data Sources

- **Character family relationships**: [Wikidata](https://www.wikidata.org/) (CC0), queried via SPARQL
- **Locations, events, and narrative relationships**: LLM-extracted (Gemini) from Samuel Butler's 1900 English prose translation ([Project Gutenberg #1727](https://www.gutenberg.org/ebooks/1727), public domain)
- **Location artwork**: individually licensed public-domain works from Wikimedia Commons (see `scripts/import_to_mongodb.py`'s `LOCATION_IMAGES` for credits)

Not the full 24 books — deliberately scoped to the most recognizable episodes rather than the entire epic.

## Known Limitations

This is a demo, not a production app:

- Small dataset (28 characters, ~150 relationship edges) — appropriate for demonstrating the technique, not a complete Odyssey knowledge base
- Depends on live Gemini and Voyage AI API calls; no offline fallback
- The adventure map uses fixed-pixel SVG coordinates and hasn't been tuned for mobile/touch devices
- Progress on the adventure map is session-only (not persisted)
