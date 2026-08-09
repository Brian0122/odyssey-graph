"""MongoDB connection — single cached client shared across Streamlit reruns.

Without st.cache_resource, Streamlit re-executes the whole script on every
interaction, which would create a new MongoClient (and new connection pool)
each time. st.cache_resource makes this a singleton for the life of the
server process, shared across all user sessions.

Pool sizing assumes a small demo app (low concurrent viewers, single Atlas
cluster, not a production OLTP workload) — adjust maxPoolSize up if this
ever serves real concurrent traffic.
"""

import streamlit as st
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.database import Database

from secrets_util import get_secret

load_dotenv()


@st.cache_resource
def get_client() -> MongoClient:
    return MongoClient(
        get_secret("MONGODB_URI"),
        maxPoolSize=20,  # demo-scale traffic; raise if this serves real concurrent users
        minPoolSize=0,  # no need to pre-warm connections for a low-traffic demo
        connectTimeoutMS=8000,
        serverSelectionTimeoutMS=8000,
    )


def get_db() -> Database:
    db_name = get_secret("MONGODB_DB_NAME", "odyssey_graph")
    return get_client()[db_name]
