"""Shared flagship demo questions — used by both the AI 問答 tab
(app/views/qa.py) and the Graph RAG comparison tab (app/views/compare.py)
so the two don't drift out of sync. Two categories, each verified against
the real data on BOTH pipelines (not just the graph side) before being
added here (see CLAUDE.md's 功能需求 section):

- Indirect relationship (point-to-point, needs 2 hops): the connection
  between the two named entities isn't stated in either one's own
  description, only $graphLookup traversal surfaces it. This reliably
  works for FAMILY/PERSON relations (CHILD_OF, FATHER_OF, SIBLING_OF,
  ANTAGONIST_OF chains) — those facts aren't naturally co-narrated in any
  single node's prose description.
- Enumeration (e.g. "all of X's children"): vector search has no way to
  guarantee completeness — it returns whatever scores as "similar", not
  every matching edge — while $graphLookup deterministically finds every
  edge off a node. Tested this is a genuinely different, often even
  starker failure mode for vector-only than the point-to-point questions
  (e.g. it didn't even retrieve Poseidon himself as a match for "who are
  Poseidon's children").
- Common-ancestor inference (Scylla/Charybdis): neither has a direct edge
  to the other — no SIBLING_OF between them — only two separate CHILD_OF
  edges to the same parent (Poseidon). Answering "how are they related"
  needs the model to notice they share a parent and infer "siblings" from
  that, one level beyond simply reading a single matching edge. Vector
  search didn't even retrieve Charybdis as a match at all.

Deliberately NOT included: EVENT-CAUSES-EVENT questions (e.g. "who
caused Zeus's Storm"). Tested and removed — unlike family relations,
event descriptions (LLM-extracted narrative summaries) tend to already
narrate cause-and-effect in their own prose ("Helios, furious, demanded
Zeus punish them..."), so vector-only answers these just fine from a
single retrieved snippet without needing the CAUSES edge at all. Doesn't
demonstrate any contrast — both pipelines succeed — so it doesn't belong
here even though it seemed like a good idea before actually testing the
vector-only side of it.

Added after the Book 5 / Books 21-24 data expansion (see CLAUDE.md's
目前進度): Laertes/Telemachus — same point-to-point indirect-relationship
category as the Telemachus/Poseidon question, tested on both pipelines
before adding (vector-only correctly finds both individually but won't
state the grandfather relationship; Graph RAG answers it via the shared
Odysseus CHILD_OF/FATHER_OF chain). Kept as an ADDITION rather than a
replacement so the demo can show off the newly-expanded content without
losing the original two-hop antagonist-god example. A "Zeus's children"
enumeration question was considered as a second use of the new data but
rejected — only 2 children (Athena, Hermes) in this dataset, weaker
demo effect than the existing Poseidon's-children question (3 children).
"""

EXAMPLE_QUESTIONS = {
    "zh": [
        "Telemachus 跟 Poseidon 有什麼關係？",
        "刺瞎波呂斐摩斯的人，跟波塞頓有什麼關係？",
        "宙斯跟波呂斐摩斯是什麼關係？",
        "波塞頓總共有哪些子女？",
        "斯庫拉跟卡律布狄斯是什麼關係？",
        "萊爾特斯跟特勒馬科斯有什麼關係？",
    ],
    "en": [
        "What is the relationship between Telemachus and Poseidon?",
        "What is the relationship between the person who blinded Polyphemus and Poseidon?",
        "What is the relationship between Zeus and Polyphemus?",
        "Who are all of Poseidon's children?",
        "What is the relationship between Scylla and Charybdis?",
        "What is the relationship between Laertes and Telemachus?",
    ],
}
