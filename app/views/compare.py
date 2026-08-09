import traceback

import streamlit as st
from streamlit_agraph import agraph, Config, Node, Edge

import theme
from i18n import get_lang, t
from agent import ask, ask_vector_only
from rag import vector_only_search
from graph_data import (
    filter_relevant_relationships,
    NODE_TYPE_COLOR,
    LABEL_FONT_COLOR,
    NODE_TYPE_SHAPE,
)
from example_questions import EXAMPLE_QUESTIONS

st.set_page_config(page_title=t("compare.page_title"), layout="wide", page_icon="⚖️")
theme.inject()

st.title(t("compare.page_title"))
st.markdown("<div class='meander-divider'></div>", unsafe_allow_html=True)
theme.atlas_badge(t("compare.badge"))
st.caption(t("compare.caption"))

with st.sidebar:
    st.subheader(t("qa.example_questions"))
    picked_question = None
    for q in EXAMPLE_QUESTIONS[get_lang()]:
        if st.button(q, use_container_width=True, key=f"compare_example_{q}"):
            picked_question = q

if picked_question:
    st.session_state.compare_question = picked_question
    st.session_state.compare_result = None  # invalidate — force a fresh run below


def relation_label(code: str) -> str:
    return t(f"relation.{code}") if code else code


def run_both_pipelines(question: str, lang: str) -> dict:
    vector_result = vector_only_search(question, lang=lang)
    vector_answer = ask_vector_only(question, vector_result["matches"], lang=lang)
    graph_answer = ask(question, lang=lang)
    return {
        "vector_matches": vector_result["matches"],
        "vector_answer": vector_answer["answer"],
        "graph_answer": graph_answer["answer"],
        "graph_retrievals": graph_answer["retrievals"],
    }


def render_subgraph(relationships: list):
    node_ids = set()
    for r in relationships:
        node_ids.add(r["source"])
        node_ids.add(r["target"])
    if not node_ids:
        return

    id_to_label = {}
    for r in relationships:
        id_to_label[r["source"]] = r["source_name"]
        id_to_label[r["target"]] = r["target_name"]

    # The relationship dicts don't carry node_type (they're edges, not
    # nodes) — a single flat color/shape stands in fine here since this
    # subgraph is only ever a handful of nodes for one specific answer,
    # not the full knowledge graph where type distinction matters more.
    nodes = [
        Node(
            id=nid,
            label=id_to_label[nid],
            color=NODE_TYPE_COLOR["character"],
            shape=NODE_TYPE_SHAPE["character"],
            size=20,
            font={"color": LABEL_FONT_COLOR, "size": 14, "strokeWidth": 3, "strokeColor": "#0a0906"},
        )
        for nid in node_ids
    ]
    edges = [
        Edge(
            source=r["source"],
            target=r["target"],
            label=relation_label(r["relation"]),
            font={"color": "#c9a24a", "size": 10, "background": "#151109", "strokeWidth": 0},
        )
        for r in relationships
    ]
    config = Config(width="100%", height=280, directed=True, physics=True,
                     interaction={"zoomView": False})
    # Config.__init__ turns width="100%" into the invalid CSS "100%px" —
    # see app/views/graph.py's comment on the same fix for why.
    config.width = "100%"
    agraph(nodes=nodes, edges=edges, config=config)


question = st.session_state.get("compare_question")

# The split-screen layout itself (headers, structure) is always visible,
# even before a question is picked — a visitor should immediately see
# "this page compares two approaches side by side" from the shape of the
# page alone, not have that revealed only after clicking something.
st.markdown(f"### {question}" if question else f"### {t('compare.select_question')}")

result = st.session_state.get("compare_result")
# Only actually run the pipelines when there's a question but no cached
# result yet — otherwise simply navigating to another tab and back would
# re-trigger both Gemini calls (and their cost) on every revisit, since
# compare_question alone persisting in session_state was enough to
# satisfy the `if question:` check below on every rerun.
if question and result is None:
    try:
        with st.spinner(t("compare.thinking")):
            result = run_both_pipelines(question, get_lang())
            st.session_state.compare_result = result
    except Exception:
        traceback.print_exc()
        st.error(t("qa.error"))

col_vector, col_graph = st.columns(2)

with col_vector:
    st.subheader(t("compare.vector_column"))
    if not result:
        st.caption(t("compare.vector_placeholder"))
    else:
        st.markdown(f"**{t('compare.snippets_heading')}**")
        for m in result["vector_matches"]:
            with st.expander(f"{m['name']} ({m['score']:.2f})"):
                st.markdown(m["description"])
        st.markdown(f"**{t('compare.answer_heading')}**")
        st.markdown(result["vector_answer"])

with col_graph:
    st.subheader(t("compare.graph_column"))
    if not result:
        st.caption(t("compare.graph_placeholder"))
    else:
        st.markdown(f"**{t('compare.answer_heading')}**")
        st.markdown(result["graph_answer"])

        all_relationships = [
            r for res in result["graph_retrievals"] for r in res["relationships"]
        ]
        relevant = filter_relevant_relationships(all_relationships, result["graph_answer"])

        st.markdown(f"**{t('compare.path_heading')}**")
        if relevant:
            for r in relevant:
                st.markdown(f"- {r['source_name']} —（{relation_label(r['relation'])}）→ {r['target_name']}")
            st.markdown(f"**{t('compare.subgraph_heading')}**")
            render_subgraph(relevant)
        else:
            st.caption(t("compare.no_path"))
