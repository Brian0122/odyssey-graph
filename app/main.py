import streamlit as st

from i18n import t

if "lang" not in st.session_state:
    st.session_state.lang = "zh"

pg = st.navigation([
    # Adventure map first — the demo's主體/門面 (see CLAUDE.md's UI 結構):
    # story experience before the underlying graph, then the split-screen
    # payoff (why Graph RAG beats vector-only), then free-form Q&A last.
    st.Page("views/map.py", title=t("map.title"), url_path="map", icon="🗺️"),
    st.Page("views/graph.py", title=t("graph.nav_title"), url_path="graph", icon="🏺"),
    st.Page("views/compare.py", title=t("compare.nav_title"), url_path="compare", icon="⚖️"),
    st.Page("views/qa.py", title=t("qa.nav_title"), url_path="qa", icon="🦉"),
])
pg.run()

# Rendered here (after pg.run()) so it sits below the page's own sidebar
# content instead of above it. Bound directly to session_state via
# key="lang" (no separate variable, no manual st.rerun()): Streamlit
# applies a widget's new value to session_state BEFORE the script starts
# re-executing, so pg.run() above already sees the updated language on
# the very same rerun that the click triggered — a manual "compare old
# vs new, then st.rerun()" pattern was firing a REDUNDANT second rerun
# stacked on Streamlit's own automatic one, which was the actual cause
# of filters/selections getting wiped after a couple of language flips.
with st.sidebar:
    st.divider()
    st.radio(
        "Language / 語言",
        options=["zh", "en"],
        format_func=lambda l: "中文" if l == "zh" else "English",
        horizontal=True,
        label_visibility="collapsed",
        key="lang",
    )
