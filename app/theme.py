"""Visual theme injection.

Base colors come from .streamlit/config.toml (streamlit-agraph's component
reads Streamlit's native theme for its internal canvas, so that's the only
reliable way to keep the graph background consistent with the page).

Background is a real photo, not hand-coded CSS/SVG: a public-domain 1903
map of ancient Greece (Wikimedia Commons, "Map of Ancient Greece (as drawn
in 1903)", public domain), processed with PIL into a dark gold-brown
duotone and blurred so it reads as atmosphere/texture rather than a
legible competing map. See scripts/process_map_background.py for the
processing steps; assets/ancient_greece_map_full.jpg is the untouched
source and assets/map_bg.jpg is the processed result.

Design note: an earlier version leaned on text-shadow glow + scattered
"star" dots + a double border — the combination read as amateurish rather
than atmospheric (glow effects and sprinkle-decoration are exactly the
cliches that make dark fantasy UIs look cheap). This version keeps that
restraint (no glow, no ornamental unicode) and adds one real textural
element instead of more hand-coded decoration.
"""

from pathlib import Path

_ASSETS = Path(__file__).parent / "assets"

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;600;700&family=EB+Garamond:ital,wght@0,400;0,600;1,400&display=swap');

:root {
  --gold: #b08d3e;
  --parchment-text: #cbb98a;
}

.stApp {
  background-image:
    linear-gradient(rgba(27, 22, 13, 0.55), rgba(27, 22, 13, 0.75)),
    url("data:image/jpeg;base64,__MAP_BG_B64__");
  background-size: cover;
  background-position: center top;
  background-attachment: fixed;
}

/* streamlit-agraph renders in its own iframe and can only take a FLAT
   color from Streamlit's theme (no way to share the page's textured
   background across the iframe boundary) — so instead of fighting for a
   seamless blend, frame it deliberately, like a map set into a window. */
[data-testid="stIFrame"] {
  border: 1px solid var(--gold);
  border-radius: 3px;
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.5);
  /* streamlit-agraph's underlying gesture library (Hammer.js, touchAction:
     "compute") sets the canvas's own touch-action CSS to claim touch
     gestures for itself, at the browser level — a layer below vis-network's
     own dragView/zoomView switches, so turning those off doesn't stop it
     from still intercepting touch scroll on mobile. Forcing pan-y on the
     OUTER iframe element (from this parent-page stylesheet) tells the
     browser to allow vertical scroll gestures starting on this element
     to reach the page, before the iframe's own inner content gets a say.
     Unverified without a real mobile browser — CSS touch-action across an
     iframe boundary is exactly the kind of thing that needs eyes-on
     testing, not just correct-looking code. */
  touch-action: pan-y !important;
}

/* Location-card artwork: source images vary wildly in aspect ratio
   (landscape prints vs. portrait plates). Forcing a fixed box meant
   either cropping content (object-fit: cover) or ugly letterbox bars
   (object-fit: contain) — neither read well against this varied a set of
   images, so instead the frame just hugs each image at its own natural
   proportions, capped so nothing gets too large. Card height varies
   between stops as a result; that's the accepted tradeoff. */
.location-image-frame {
  max-width: 100%;
  width: fit-content;
  margin: 1.2em auto 0.4em auto;
  border: 1px solid var(--gold);
  border-radius: 3px;
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.5);
  overflow: hidden;
}
.location-image-frame img {
  display: block;
  max-width: 100%;
  max-height: 420px;
  width: auto;
  height: auto;
}
.location-image-credit {
  text-align: center;
  font-family: 'EB Garamond', serif;
  font-style: italic;
  font-size: 0.85em;
  color: var(--gold);
  opacity: 0.75;
  margin-bottom: 1em;
}

.block-container {
  font-family: 'EB Garamond', Georgia, serif;
}

h1 {
  font-family: 'Cinzel', serif !important;
  font-weight: 600 !important;
  color: var(--parchment-text) !important;
  text-align: center;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  font-size: 1.9rem !important;
  padding-bottom: 0.3em;
  margin-bottom: 0 !important;
}

/* Greek meander (key pattern) divider — the actual repeating geometric
   motif found on Greek pottery and temple friezes. A specific, recognizable
   signifier of "ancient Greek" that generic gold trim/glow is not. */
.meander-divider {
  height: 14px;
  margin: 0 auto 1.4em auto;
  max-width: 420px;
  background-image: url("data:image/svg+xml;utf8,\
<svg xmlns='http://www.w3.org/2000/svg' width='40' height='14'>\
<path d='M0,14 L0,4 L8,4 L8,10 L16,10 L16,0 L24,0 L24,10 L32,10 L32,4 L40,4 L40,14' \
stroke='%23b08d3e' stroke-width='1.6' fill='none'/></svg>");
  background-repeat: repeat-x;
  background-position: center;
  opacity: 0.8;
}

.epigraph {
  text-align: center;
  font-family: 'EB Garamond', serif;
  font-style: italic;
  font-size: 1.05rem;
  color: var(--parchment-text);
  opacity: 0.7;
  max-width: 560px;
  margin: 0 auto 1.6em auto;
  line-height: 1.6;
}

h2, h3 {
  font-family: 'Cinzel', serif !important;
  font-weight: 600 !important;
  color: var(--parchment-text) !important;
  letter-spacing: 0.06em;
  font-size: 1rem !important;
  text-transform: uppercase;
}

[data-testid="stCaptionContainer"], .stCaption {
  font-family: 'EB Garamond', serif !important;
  font-style: italic;
  color: var(--gold) !important;
  text-align: center;
  opacity: 0.75;
  letter-spacing: 0.02em;
}

[data-testid="stSidebar"] {
  background: rgba(10, 11, 15, 0.55) !important;
}
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
  font-family: 'Cinzel', serif !important;
  font-size: 0.85rem !important;
  color: var(--parchment-text) !important;
  letter-spacing: 0.08em;
}

/* Native widgets (buttons, selectbox, expander, chat input, dividers)
   default to Streamlit's neutral gray styling regardless of
   .streamlit/config.toml's primaryColor — that only feeds BaseWeb's
   theme provider for things like checkbox/radio fill color, not these.
   Left alone they read as generic gray controls dropped into an
   otherwise fully-themed gold/parchment page. Selectors verified against
   the actual installed streamlit==1.61.1 frontend JS bundle (grepped for
   the real data-testid strings), not assumed from memory — this layer
   changes across Streamlit versions. */
[data-testid^="stBaseButton-"] {
  background-color: rgba(176, 141, 62, 0.08) !important;
  border: 1px solid var(--gold) !important;
  border-radius: 3px !important;
  color: var(--parchment-text) !important;
  font-family: 'EB Garamond', serif !important;
}
[data-testid^="stBaseButton-"]:hover {
  background-color: rgba(176, 141, 62, 0.22) !important;
  border-color: var(--gold) !important;
  color: var(--parchment-text) !important;
}

/* Selectbox's actual clickable control (BaseWeb Select) has no stable
   class name across versions, but always exposes role="combobox" per
   WAI-ARIA — targeting that instead of guessing internal div nesting. */
[data-testid="stSelectbox"] [role="combobox"] {
  border-color: var(--gold) !important;
  border-radius: 3px !important;
}

[data-testid="stChatInput"] {
  border-color: var(--gold) !important;
  border-radius: 3px !important;
}

[data-testid="stExpanderDetails"] {
  border: 1px solid var(--gold) !important;
  border-radius: 3px !important;
}
[data-testid="stExpanderDetails"] summary {
  font-family: 'EB Garamond', serif !important;
  color: var(--parchment-text) !important;
}

/* st.divider() renders a plain <hr> with no dedicated testid — left at
   its default gray it reads as an unstyled seam every place it's used
   (sidebar sections, page dividers). */
hr {
  border-color: var(--gold) !important;
  opacity: 0.35;
}

/* Technical-attribution badge ("Powered by Atlas ..."). Deliberately NOT
   styled like .stCaption (italic, faint, opacity 0.75) — that's exactly
   why it read as invisible before. A solid bordered pill in the same
   Cinzel small-caps voice as the page headers reads as a label, not a
   footnote, without resorting to glow/color tricks outside the theme. */
.atlas-badge-wrap {
  display: flex;
  justify-content: center;
  margin-bottom: 1.1em;
}
.atlas-badge {
  display: inline-block;
  padding: 0.4em 1.1em;
  border: 1px solid var(--gold);
  border-radius: 999px;
  background: rgba(176, 141, 62, 0.16);
  font-family: 'Cinzel', serif;
  font-weight: 600;
  font-size: 0.72rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--parchment-text);
  white-space: nowrap;
}

.odyssey-legend {
  display: flex;
  justify-content: center;
  gap: 2.5em;
  font-family: 'EB Garamond', serif;
  font-size: 0.95em;
  color: var(--parchment-text);
  opacity: 0.85;
  margin-bottom: 0.8em;
}
.odyssey-legend span.dot {
  font-size: 1em;
  margin-right: 0.35em;
}
</style>
"""


def inject():
    import streamlit as st
    map_bg_b64 = (_ASSETS / "map_bg_b64.txt").read_text()
    st.markdown(CSS.replace("__MAP_BG_B64__", map_bg_b64), unsafe_allow_html=True)


def atlas_badge(text: str):
    """Technical-attribution badge — see the CSS comment on .atlas-badge
    for why this exists as its own component instead of st.caption: every
    page previously used st.caption for this, which the page's own theme
    styles as small/italic/75%-opacity, exactly the opposite of what an
    attribution badge needs on a "look how fun this map/graph is" screen.
    """
    import streamlit as st
    st.markdown(f"<div class='atlas-badge-wrap'><span class='atlas-badge'>{text}</span></div>",
                unsafe_allow_html=True)
