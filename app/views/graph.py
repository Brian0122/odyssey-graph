import streamlit as st
from streamlit_agraph import agraph, Config, Node, Edge

import theme
from i18n import get_lang, t
from graph_data import (
    fetch_graph_data,
    filter_graph,
    dedupe_family_edges_for_display,
    graphlookup_ego_network,
    NODE_TYPE_COLOR,
    LABEL_FONT_COLOR,
    NODE_TYPE_SHAPE,
    NODE_TYPE_GLYPH,
)

st.set_page_config(page_title=t("graph.page_title"), layout="wide", page_icon="🏺")
theme.inject()

NODE_TYPE_LABEL = {
    "character": t("node_type.character"),
    "location": t("node_type.location"),
    "event": t("node_type.event"),
}

# Relation codes are the canonical, queryable values in MongoDB — this map
# is purely for human-readable display on the graph edges.
RELATION_LABEL = {
    "CHILD_OF": t("relation.CHILD_OF"),
    "FATHER_OF": t("relation.FATHER_OF"),
    "MOTHER_OF": t("relation.MOTHER_OF"),
    "PARENT_OF": t("relation.PARENT_OF"),
    "MARRIED_TO": t("relation.MARRIED_TO"),
    "SIBLING_OF": t("relation.SIBLING_OF"),
    "ANTAGONIST_OF": t("relation.ANTAGONIST_OF"),
    "BLINDS": t("relation.BLINDS"),
    "CAUSES": t("relation.CAUSES"),
    "PARTICIPATES_IN": t("relation.PARTICIPATES_IN"),
    "LOCATED_AT": t("relation.LOCATED_AT"),
    "KILLS": t("relation.KILLS"),
    "PUNISHES": t("relation.PUNISHES"),
    "PRECEDES": t("relation.PRECEDES"),
    "PROTECTOR_OF": t("relation.PROTECTOR_OF"),
}

st.title(t("graph.page_title"))
st.markdown("<div class='meander-divider'></div>", unsafe_allow_html=True)
st.markdown(
    f"<p class='epigraph'>{t('graph.epigraph')}</p>",
    unsafe_allow_html=True,
)
theme.atlas_badge(t("graph.badge"))

full_data = fetch_graph_data(lang=get_lang())
character_nodes = sorted(
    [n for n in full_data["nodes"] if n["node_type"] == "character"],
    key=lambda n: n["label"],
)

with st.sidebar:
    st.subheader(t("graph.filters"))

    # st.multiselect turned out to be the actual culprit for state loss
    # across a language switch: its selected "chips" weren't re-translating
    # on rerun either, which points at the frontend matching/keying
    # selected options by their rendered LABEL text rather than by the
    # underlying value — so changing a label (via format_func, driven by
    # NODE_TYPE_LABEL) for an already-selected value could desync the
    # frontend's selection from the backend's session_state. Three
    # independent checkboxes have no "list of options" to desync at all;
    # each is just its own bool, immune to this class of bug.
    st.caption(t("graph.show_types"))
    show_types = []
    if st.checkbox(t("node_type.character"), value=True, key="show_character"):
        show_types.append("character")
    if st.checkbox(t("node_type.location"), value=False, key="show_location"):
        show_types.append("location")
    if st.checkbox(t("node_type.event"), value=False, key="show_event"):
        show_types.append("event")

    # PARTICIPATES_IN is the only edge connecting characters to events, so
    # hiding it whenever "事件" isn't selected keeps the default view
    # clean — but hiding it even when the user explicitly asked to see
    # events would make those events show up with no connections at all.
    # Tie the two together instead of a separate, easy-to-miss toggle.
    exclude_relations = set() if "event" in show_types else {"PARTICIPATES_IN"}

    # Options are node IDs (language-independent) with format_func doing
    # the display translation, rather than translated label strings as
    # the options themselves — otherwise the previously-selected value
    # (e.g. "奧德修斯") wouldn't match any option after switching to
    # English ("Odysseus") and the selection would silently reset.
    id_to_label = {n["id"]: n["label"] for n in character_nodes}
    st.caption(t("graph.focus_select"))
    focus_node_id = st.selectbox(
        "focus_node_id",
        options=[None] + [n["id"] for n in character_nodes],
        format_func=lambda cid: t("graph.show_all") if cid is None else id_to_label[cid],
        key="focus_node_id",
        label_visibility="collapsed",
    )

    use_graphlookup = st.checkbox(
        t("graph.use_graphlookup"),
        value=True,
        help=t("graph.use_graphlookup_help"),
        key="use_graphlookup",
    )
    # (Checkbox keeps its translated inline label — unlike the two widgets
    # above, its value is a trivial bool that isn't painful to lose, so
    # it doesn't need the label-collapsing workaround.)

if focus_node_id and use_graphlookup:
    data = graphlookup_ego_network(
        full_data["nodes"],
        focus_node_id=focus_node_id,
        node_types=set(show_types),
        exclude_relations=exclude_relations,
        focus_depth=2,
        lang=get_lang(),
    )
else:
    data = filter_graph(
        full_data,
        node_types=set(show_types),
        exclude_relations=exclude_relations,
        focus_node_id=focus_node_id,
    )
data["edges"] = dedupe_family_edges_for_display(data["edges"])

nodes = [
    Node(
        id=n["id"],
        label=n["label"],
        color=NODE_TYPE_COLOR[n["node_type"]],
        shape=NODE_TYPE_SHAPE[n["node_type"]],
        size=28 if n["id"] == focus_node_id else (24 if n["node_type"] == "character" else 17),
        font={"color": LABEL_FONT_COLOR, "size": 18, "strokeWidth": 3, "strokeColor": "#0a0906"},
        # Native vis-network hover tooltip — same mechanism already used for
        # edge descriptions below, just applied to nodes too.
        title=n.get("description") or n["label"],
    )
    for n in data["nodes"]
]
edges = [
    Edge(
        source=e["source"],
        target=e["target"],
        label=RELATION_LABEL.get(e["relation"], e["relation"]),
        title=e.get("description") or RELATION_LABEL.get(e["relation"], e["relation"]),
        width=2.5,
        # Distinct from node labels on purpose: muted gold (vs. the node's
        # bright parchment) + a solid background "chip" so it reads as a
        # tag sitting on the line, not another floating node label.
        font={"color": "#c9a24a", "size": 15, "background": "#151109",
              "strokeWidth": 0},
    )
    for e in data["edges"]
]

config = Config(
    width="100%",
    height=800,
    directed=True,
    physics=True,
    hierarchical=False,
    collapsible=False,
    # zoomView back on (was off — scroll-to-zoom used to fight with
    # scrolling the page when the cursor happened to be over the graph).
    # Re-enabled to let people zoom into a crowded cluster on desktop now
    # that the dataset has grown to 67 nodes; the scroll-conflict tradeoff
    # is back too — trying this deliberately, revert to False if it reads
    # as more annoying than useful.
    interaction={"zoomView": True},
)
# Config.__init__ always does self.width = f"{width}px" — passing the
# string "100%" (as above) produces the literal, invalid CSS value
# "100%px", not a percentage. The class was only ever designed to take a
# raw pixel number; there's no constructor way to get a true responsive
# percentage width. Overwrite the attribute directly with a valid value
# after construction — this is almost certainly why the graph wasn't
# shrinking to fit narrower (e.g. mobile) viewports: the invalid value
# likely fell back to some non-responsive default instead of actually
# scaling with the container.
config.width = "100%"

# streamlit-agraph's Config() only exposes a handful of top-level physics
# knobs (solver name, timestep, min/maxVelocity) — barnesHut's own spacing
# options (springLength, avoidOverlap) aren't constructor kwargs, but
# config.physics is just a plain dict that gets serialized as-is, so they
# can be added directly. Default barnesHut spacing (springLength ~95) was
# fine for the original ~45-node graph but reads as cramped/overlapping
# labels now that the dataset has grown to 67 nodes (see CLAUDE.md's 資料
# 擴充 entry).
#
# First attempt pushed springLength to 220 and lowered centralGravity —
# fixed the overlap but made everything look tiny, because vis-network
# auto-fits the WHOLE graph into the fixed-size canvas on stabilization: a
# physically bigger graph (more spread out) gets zoomed out further to
# still fit, shrinking every node/label along with it. Dialed spacing back
# to a smaller bump and left centralGravity at its default (pulls the
# graph back toward center, keeping the overall footprint — and therefore
# the auto-fit zoom level — from ballooning), and raised base node/font
# sizes above so what's left after that unavoidable zoom-out still reads
# clearly instead of relying on spacing tweaks alone.
config.physics["barnesHut"] = {
    "springLength": 150,
    "avoidOverlap": 0.5,
}

legend_items = "".join(
    f"<span><span class='dot' style='color:{color}'>{NODE_TYPE_GLYPH[node_type]}</span>{NODE_TYPE_LABEL[node_type]}</span>"
    for node_type, color in NODE_TYPE_COLOR.items()
)
st.markdown(f"<div class='odyssey-legend'>{legend_items}</div>", unsafe_allow_html=True)

if data["nodes"]:
    agraph(nodes=nodes, edges=edges, config=config)
else:
    st.info(t("graph.no_nodes"))

st.caption(t("graph.footer", nodes=len(nodes), edges=len(edges)))
