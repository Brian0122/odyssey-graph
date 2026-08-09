"""Single place every module reads API keys/config from — see CLAUDE.md's
限制 section: never touch .env's contents, always read secrets via
python-dotenv (os.environ).

Locally that's the whole story: load_dotenv() populates os.environ from
.env and plain os.environ.get() is enough. Deploying to Streamlit
Community Cloud changes this: secrets are pasted into the app's Settings
> Secrets panel as TOML, not a committed .env file. Streamlit's own docs
confirm root-level secrets.toml entries are "also accessible as
environment variables" for local secrets.toml, but don't explicitly
reconfirm that for Cloud-panel-entered secrets — st.secrets is the only
access path Streamlit's Cloud-specific docs actually guarantee. Rather
than gamble on undocumented behavior carrying over, this tries
os.environ first (so local dev via .env is untouched) and falls back to
st.secrets (guaranteed to work on Cloud) — works regardless of which
assumption turns out to be true.
"""

import os


def get_secret(key: str, default: str | None = None) -> str | None:
    value = os.environ.get(key)
    if value is not None:
        return value

    try:
        import streamlit as st
        value = st.secrets.get(key)
    except Exception:
        value = None
    if value is not None:
        return value

    if default is not None:
        return default
    raise KeyError(f"{key} not found in os.environ or st.secrets")
