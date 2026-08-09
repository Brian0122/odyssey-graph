import base64
from pathlib import Path

import streamlit as st

import theme
from i18n import get_lang, t
from map_data import fetch_characters_for_location, fetch_events_for_location, fetch_locations
from components.odyssey_map import odyssey_map

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
_MIME_BY_SUFFIX = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}


def render_location_image(image_path: Path, credit: str | None):
    mime = _MIME_BY_SUFFIX.get(image_path.suffix.lower(), "image/jpeg")
    b64 = base64.b64encode(image_path.read_bytes()).decode()
    st.markdown(
        f"<div class='location-image-frame'><img src='data:{mime};base64,{b64}' /></div>",
        unsafe_allow_html=True,
    )
    if credit:
        st.markdown(f"<p class='location-image-credit'>{credit}</p>", unsafe_allow_html=True)

st.set_page_config(page_title=t("map.page_title"), layout="wide", page_icon="🗺️")
theme.inject()

st.title(t("map.title"))
st.markdown("<div class='meander-divider'></div>", unsafe_allow_html=True)
st.markdown(
    f"<p class='epigraph'>{t('map.epigraph')}</p>",
    unsafe_allow_html=True,
)
theme.atlas_badge(t("map.badge"))
st.caption(t("map.caption"))

locations = fetch_locations(lang=get_lang())

if "unlocked_order" not in st.session_state:
    st.session_state.unlocked_order = 1
if "selected_location_id" not in st.session_state:
    st.session_state.selected_location_id = locations[0]["id"] if locations else None

max_order = max((loc["order"] for loc in locations), default=1)

with st.sidebar:
    st.subheader(t("map.progress"))
    st.progress(st.session_state.unlocked_order / max_order)
    st.caption(t("map.progress_caption", n=st.session_state.unlocked_order, max=max_order))
    if st.button(t("map.unlock_all"), use_container_width=True):
        st.session_state.unlocked_order = max_order
        st.session_state._instant_unlock = True
        st.rerun()
    if st.button(t("map.restart"), use_container_width=True):
        st.session_state.unlocked_order = 1
        st.session_state.selected_location_id = locations[0]["id"] if locations else None
        st.rerun()

clicked_id = odyssey_map(
    locations=locations,
    unlocked_order=st.session_state.unlocked_order,
    instant=st.session_state.pop("_instant_unlock", False),
    fogged_label=t("map.fogged_label"),
    key="odyssey_map",
)

by_id = {loc["id"]: loc for loc in locations}

# The component keeps returning the same clicked_id across reruns until the
# frontend sets a new one — dedup against the last id we actually acted on,
# otherwise the forced st.rerun() below (needed to redraw the map's fog
# immediately) would loop forever re-processing the same click.
if clicked_id and clicked_id in by_id and clicked_id != st.session_state.get("_last_processed_click"):
    st.session_state._last_processed_click = clicked_id
    clicked_order = by_id[clicked_id]["order"]
    st.session_state.selected_location_id = clicked_id
    if clicked_order == st.session_state.unlocked_order + 1:
        st.session_state.unlocked_order = clicked_order
        st.rerun()

st.markdown("<div class='meander-divider'></div>", unsafe_allow_html=True)

selected = by_id.get(st.session_state.selected_location_id)
if selected and selected["order"] <= st.session_state.unlocked_order:
    st.subheader(f"{selected['order']}. {selected['name']}")
    if selected.get("book_chapter"):
        st.caption(selected["book_chapter"])

    st.markdown(selected["description"])

    lang = get_lang()
    events = fetch_events_for_location(selected["id"], lang=lang)
    characters = fetch_characters_for_location(selected["id"], lang=lang)

    col1, col2 = st.columns(2)
    with col1:
        if events:
            st.markdown(f"**{t('map.events_heading')}**")
            for ev in events:
                with st.expander(ev["name"]):
                    st.markdown(ev["description"])
                    if ev.get("source_excerpt"):
                        st.caption(t("map.source_excerpt", excerpt=ev["source_excerpt"]))
    with col2:
        if characters:
            st.markdown(f"**{t('map.characters_heading')}**")
            for c in characters:
                with st.expander(c["name"]):
                    st.markdown(c["description"])

    if selected.get("image"):
        image_path = ASSETS_DIR / selected["image"]
        if image_path.exists():
            render_location_image(image_path, selected.get("image_credit"))
else:
    st.info(t("map.not_started"))

st.caption(t("map.footer"))
