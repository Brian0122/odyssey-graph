"""AI Agent for the 自然語言查詢 ("AI 問答") tab — Gemini function calling
wrapping app/rag.py's graph_rag_retrieve as a tool.

All Gemini-specific details (SDK calls, tool schema, response parsing)
are contained in this one module. The rest of the app only calls `ask()`
and never touches the Gemini SDK directly — if the project ever switches
LLM providers, only this file's internals need rewriting.

Verified against the actually-installed google-genai 2.17.0 SDK (field
names checked via introspection, not recalled from training — this
package's API has changed release to release).
"""

import json

from dotenv import load_dotenv
from google import genai
from google.genai import types

from rag import graph_rag_retrieve
from graph_data import dedupe_family_edges_for_display
from secrets_util import get_secret

load_dotenv()

MODEL = get_secret("GEMINI_MODEL", "gemini-3.6-flash")

_VECTOR_ONLY_SYSTEM_INSTRUCTION = """You are answering questions about Homer's Odyssey using \
ONLY the text snippets provided below — these come from semantic search alone, with no \
relationship/graph data attached, just descriptive text about individually-matched \
characters/locations/events.

Rules:
- Base your answer strictly on the snippets given. Do not use outside knowledge of the \
Odyssey, and do not infer or guess at any relationship that isn't explicitly stated in the \
snippets themselves.
- If the snippets don't contain enough information to answer (e.g. two people are each \
described individually but no snippet states how they're connected), say so plainly instead \
of guessing — this is expected and correct when the question asks about an indirect \
relationship that only graph traversal, not semantic search, can surface.
- Answer in the same language as the question."""

_SYSTEM_INSTRUCTION = """You are the Odyssey Graph assistant, answering questions about \
Homer's Odyssey (Books 9-12, Odysseus's wanderings) using a MongoDB Atlas knowledge graph.

You have one tool, search_odyssey_graph, which combines semantic vector search with graph \
traversal ($graphLookup) — it returns matched characters/locations/events AND the \
relationship edges connecting them, not just descriptive text.

Rules:
- Always call the tool at least once before answering a question about the story.
- Base your answer only on the tool's results. If the tool doesn't return enough to answer, \
say so — do not invent relationships or events not present in the results.
- When your answer relies on an indirect relationship (e.g. A is connected to B via C), explain \
it in plain prose — don't write it out as a formal path notation like "A -(relation)-> B".
- When your answer relies on a specific event, mention it by name so the source excerpt can be \
shown alongside your answer.
- Answer in the same language as the question."""

_TOOL = types.Tool(function_declarations=[
    types.FunctionDeclaration(
        name="search_odyssey_graph",
        description=(
            "Search the Odyssey knowledge graph. Combines semantic search (finds characters/"
            "locations/events relevant to the query's meaning) with graph traversal (expands "
            "the relationships connected to whatever it finds) — use this for both descriptive "
            "questions ('who is X') and relationship questions ('how are X and Y connected')."
        ),
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "A natural-language search query in English.",
                },
            },
            "required": ["query"],
        },
    )
])


def _run_tool(args: dict, lang: str) -> dict:
    return graph_rag_retrieve(args["query"], lang=lang)


def ask(question: str, lang: str = "zh", max_tool_calls: int = 3) -> dict:
    """Answer a natural-language question about the Odyssey.

    Returns {"answer": str, "retrievals": [dict, ...]} — `retrievals` is
    every graph_rag_retrieve() result the tool call(s) produced, in call
    order, so the UI can render an inline-citation panel (relationship
    paths + source excerpts) independent of whatever the model's own
    prose happens to mention.
    """
    client = genai.Client(api_key=get_secret("GEMINI_API_KEY"))
    config = types.GenerateContentConfig(
        system_instruction=_SYSTEM_INSTRUCTION,
        tools=[_TOOL],
        # This task is "phrase structured retrieval results as an answer",
        # not open-ended problem solving — measured no answer-quality
        # difference vs. the (model-dependent) default thinking level,
        # but ~40% lower cost per question (thinking tokens bill at the
        # output rate, and were the single largest cost line item).
        thinking_config=types.ThinkingConfig(thinking_level="low"),
    )

    contents = [types.Content(role="user", parts=[types.Part(text=question)])]
    retrievals = []

    for _ in range(max_tool_calls):
        response = client.models.generate_content(model=MODEL, contents=contents, config=config)

        if not response.function_calls:
            return {"answer": response.text, "retrievals": retrievals}

        # Gemini's content model only has "user"/"model" roles — a
        # function result is sent back as a "user" turn, there's no
        # separate tool/function role (unlike Anthropic's tool_result
        # blocks or OpenAI's "tool" role).
        contents.append(response.candidates[0].content)
        response_parts = []
        for fc in response.function_calls:
            result = _run_tool(fc.args, lang)
            retrievals.append(result)  # full, un-trimmed — UI citations panel wants everything
            response_parts.append(
                types.Part.from_function_response(
                    name=fc.name,
                    # Trim to what the model actually needs — full match/
                    # relationship objects, not the raw vector score noise.
                    # dedupe_family_edges_for_display also collapses
                    # redundant pairs (e.g. FATHER_OF + PARENT_OF for the
                    # same two people, from different source pipelines —
                    # see docs/schema.md) down to one: no information
                    # lost, ~18% smaller relationships payload measured.
                    response={
                        "matches": [
                            {"name": m["name"], "node_type": m["node_type"], "description": m["description"]}
                            for m in result["matches"]
                        ],
                        "relationships": dedupe_family_edges_for_display(result["relationships"]),
                    },
                )
            )
        contents.append(types.Content(role="user", parts=response_parts))

    # Ran out of tool-call budget — ask once more without tools to force
    # a final text answer from whatever's been gathered so far.
    final = client.models.generate_content(
        model=MODEL, contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=_SYSTEM_INSTRUCTION,
            thinking_config=types.ThinkingConfig(thinking_level="low"),
        ),
    )
    return {"answer": final.text, "retrievals": retrievals}


def ask_vector_only(question: str, matches: list, lang: str = "zh") -> dict:
    """Answer using ONLY vector-search snippets, no graph traversal — the
    deliberately weaker "純向量 RAG" side of the split-screen comparison
    (see app/views/compare.py). Unlike ask(), this is a single call with
    no tool loop: retrieval already happened (rag.vector_only_search) —
    the model is only asked to synthesize prose from the given snippets,
    and to honestly decline when they don't actually show the requested
    connection, rather than guessing.
    """
    client = genai.Client(api_key=get_secret("GEMINI_API_KEY"))
    snippets = "\n\n".join(
        f"[{m['node_type']}] {m['name']}: {m['description']}" for m in matches
    )
    prompt = f"Snippets:\n{snippets}\n\nQuestion: {question}"

    response = client.models.generate_content(
        model=MODEL,
        contents=[types.Content(role="user", parts=[types.Part(text=prompt)])],
        config=types.GenerateContentConfig(
            system_instruction=_VECTOR_ONLY_SYSTEM_INSTRUCTION,
            thinking_config=types.ThinkingConfig(thinking_level="low"),
        ),
    )
    return {"answer": response.text}
