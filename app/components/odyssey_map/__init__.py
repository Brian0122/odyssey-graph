"""Custom Streamlit component: the adventure map with fog-of-war.

Native Streamlit widgets can't do progressive-reveal/fog rendering, so
this is a small static HTML/SVG/JS component (no npm build step — just a
plain index.html implementing Streamlit's raw postMessage component
protocol directly). See frontend/index.html.

Bidirectional contract:
  in  -> {"locations": [...], "unlocked_order": int, "instant": bool, "fogged_label": str}
  out -> the clicked location's id (str), or None if nothing clicked yet
"""

from pathlib import Path

import streamlit.components.v1 as components

_FRONTEND_DIR = Path(__file__).parent / "frontend"

_component = components.declare_component("odyssey_map", path=str(_FRONTEND_DIR))


def odyssey_map(locations: list[dict], unlocked_order: int, instant: bool = False,
                 fogged_label: str = "？？？", key: str | None = None):
    """`instant`: skip the one-station-at-a-time reveal animation and jump
    straight to `unlocked_order` — used by the "解鎖全部" button, which
    should feel immediate rather than replaying the whole voyage.

    `fogged_label`: placeholder text drawn over not-yet-unlocked nodes
    (language-dependent — see app/i18n.py).
    """
    return _component(locations=locations, unlocked_order=unlocked_order,
                       instant=instant, fogged_label=fogged_label, key=key, default=None)
