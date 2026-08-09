"""
Step 6b: Generate bilingual name.zh + description{en,zh} for canonical
characters, grounded in their role in the extracted narrative (using the
extraction(s) already produced by extract_books.py so terminology stays
consistent with event/relationship text, e.g. Polyphemus's Chinese name
matches what's already used in extraction_gemini.json).

Only generates enrichment for characters NOT ALREADY in
data/characters_enriched.json — existing entries are kept as-is rather
than regenerated, so expanding the character list (e.g. adding Book 5 /
Books 21-24 characters) can't silently drift the wording of the original,
already-demo-verified 18 characters' bios. Run again any time new slugs
are added to characters_canonical.json; it's a no-op for slugs already
enriched.

Output: data/characters_enriched.json
"""

import json
import os
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from google import genai
from google.genai import types
from opencc import OpenCC
from pydantic import BaseModel

load_dotenv()

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CANONICAL_PATH = DATA_DIR / "characters_canonical.json"
OUTPUT_PATH = DATA_DIR / "characters_enriched.json"

# All extraction batches (see scripts/extract_books.py's BATCHES) that
# might mention a character — used only as grounding context for the
# prompt, not resolved/merged the way import_to_mongodb.py needs to.
EXTRACTION_PATHS = [
    DATA_DIR / "extraction_gemini.json",
    DATA_DIR / "extraction_gemini_book5.json",
    DATA_DIR / "extraction_gemini_books21-24.json",
]

MODEL = "gemini-3.1-flash-lite"
_CC = OpenCC("s2twp")


class CharacterEnrichment(BaseModel):
    slug: str
    name_zh: str
    description_en: str
    description_zh: str


class EnrichmentResult(BaseModel):
    characters: List[CharacterEnrichment]


def build_prompt(new_chars: list, extraction: dict) -> str:
    char_lines = "\n".join(
        f"- slug: \"{c['slug']}\" — {c['name_en']}, type: {c['type']}, note: {c.get('note', '')}"
        for c in new_chars
    )
    return f"""Given this list of Odyssey characters and the already-extracted
events/relationships involving them, generate for EACH character (use every
slug exactly once):

- `name_zh`: the standard Traditional Chinese name used for this figure in
  Greek mythology (e.g. Odysseus -> 奧德修斯). Use terminology CONSISTENT
  with any Chinese text already appearing in the extraction JSON below for
  the same figure, if present.
- `description_en`: a concise 1-2 sentence bio grounded in their role in
  THIS narrative (the events/relationships below), not a generic mythology
  summary.
- `description_zh`: the same bio in natural Traditional Chinese, written for
  a reader who hasn't read Homer (not a literal translation).

## Characters
{char_lines}

## Already-extracted events/relationships (for terminology consistency and
role context)
{json.dumps(extraction, ensure_ascii=False, indent=2)}
"""


def main():
    api_key = os.environ["GEMINI_API_KEY"]
    client = genai.Client(api_key=api_key)

    with open(CANONICAL_PATH, encoding="utf-8") as f:
        canonical_chars = json.load(f)

    existing = []
    if OUTPUT_PATH.exists():
        with open(OUTPUT_PATH, encoding="utf-8") as f:
            existing = json.load(f)
    existing_slugs = {e["slug"] for e in existing}

    new_chars = [c for c in canonical_chars if c["slug"] not in existing_slugs]
    if not new_chars:
        print("No new characters to enrich — characters_enriched.json is already up to date.")
        return

    extraction = {"locations": [], "events": [], "relationships": []}
    for path in EXTRACTION_PATHS:
        if not path.exists():
            continue
        with open(path, encoding="utf-8") as f:
            batch = json.load(f)
        for key in extraction:
            extraction[key].extend(batch.get(key, []))

    prompt = build_prompt(new_chars, extraction)

    print(f"Calling {MODEL} to enrich {len(new_chars)} new character(s): "
          f"{[c['slug'] for c in new_chars]}...")
    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=EnrichmentResult,
        ),
    )

    result: EnrichmentResult = response.parsed
    by_slug = {c.slug: c for c in result.characters}

    missing = [c["slug"] for c in new_chars if c["slug"] not in by_slug]
    if missing:
        print(f"WARNING: missing enrichment for slugs: {missing}")

    new_output = []
    for c in new_chars:
        enr = by_slug.get(c["slug"])
        new_output.append({
            "slug": c["slug"],
            "name_zh": _CC.convert(enr.name_zh) if enr else "",
            "description_en": enr.description_en if enr else "",
            "description_zh": _CC.convert(enr.description_zh) if enr else "",
        })

    output = existing + new_output
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"Wrote enrichment for {len(new_output)} new character(s) "
          f"({len(output)} total) to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
