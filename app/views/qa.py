import traceback

import streamlit as st

import theme
from i18n import get_lang, t
from agent import ask
from graph_data import filter_relevant_relationships
from example_questions import EXAMPLE_QUESTIONS

st.set_page_config(page_title=t("qa.page_title"), layout="wide", page_icon="🦉")
theme.inject()

st.title(t("qa.page_title"))
st.markdown("<div class='meander-divider'></div>", unsafe_allow_html=True)
st.markdown(f"<p class='epigraph'>{t('qa.epigraph')}</p>", unsafe_allow_html=True)
theme.atlas_badge(t("qa.caption"))

if "qa_messages" not in st.session_state:
    st.session_state.qa_messages = []

with st.sidebar:
    st.subheader(t("qa.example_questions"))
    pending_question = None
    for q in EXAMPLE_QUESTIONS[get_lang()]:
        if st.button(q, use_container_width=True, key=f"example_{q}"):
            pending_question = q
    st.divider()
    if st.button(t("qa.clear_chat"), use_container_width=True):
        st.session_state.qa_messages = []
        st.rerun()


def relation_label(code: str) -> str:
    return t(f"relation.{code}") if code else code


def render_citations(answer_text: str, retrievals: list):
    all_citations = [c for result in retrievals for c in result["citations"]]
    all_relationships = [r for result in retrievals for r in result["relationships"]]
    relevant_relationships = filter_relevant_relationships(all_relationships, answer_text)

    if not all_citations and not relevant_relationships:
        st.caption(t("qa.no_citations"))
        return

    with st.expander(t("qa.citations_heading")):
        for r in relevant_relationships:
            st.markdown(f"- {r['source_name']} —（{relation_label(r['relation'])}）→ {r['target_name']}")

        seen_ids = set()
        for c in all_citations:
            if c["id"] in seen_ids:
                continue
            seen_ids.add(c["id"])
            st.caption(t("qa.source_excerpt", excerpt=c["source_excerpt"]))


for msg in st.session_state.qa_messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant":
            render_citations(msg["content"], msg.get("retrievals", []))

typed_question = st.chat_input(t("qa.input_placeholder"))
question = pending_question or typed_question

if question:
    st.session_state.qa_messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        try:
            with st.spinner(t("qa.thinking")):
                result = ask(question, lang=get_lang())
            st.markdown(result["answer"])
            render_citations(result["answer"], result["retrievals"])
        except Exception:
            # Full traceback goes to the server log for debugging, not the
            # UI — an unhandled exception here would otherwise surface as
            # Streamlit's raw Python stack trace in front of a demo
            # audience (e.g. a transient Voyage AI rate limit that outlasts
            # rag.py's own retries).
            traceback.print_exc()
            st.error(t("qa.error"))
            result = {"answer": t("qa.error"), "retrievals": []}

    st.session_state.qa_messages.append({
        "role": "assistant",
        "content": result["answer"],
        "retrievals": result["retrievals"],
    })
