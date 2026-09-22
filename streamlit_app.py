"""Streamlit Cloud entrypoint. Validates the database connection before launching the dashboard."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st

# Validate database configuration before starting the app
try:
    from scripts.config import get_db_config
    cfg = get_db_config()
except Exception as e:
    st.error(
        "Database configuration failed. Set POSTGRES_HOST, POSTGRES_PORT, "
        "POSTGRES_DB, POSTGRES_USER, and POSTGRES_PASSWORD in your environment "
        "or Streamlit secrets.\n\nError: " + str(e)
    )
    st.stop()

# Check the connection itself
try:
    from scripts.database import test_connection
    ok, msg = test_connection()
    if not ok:
        st.error(
            "Could not connect to the database. Double-check the POSTGRES_* "
            "values (host, port, user, password).\n\nConnection error: " + msg
        )
        st.stop()
except Exception as e:
    st.error("Database connection test failed.\n\nError: " + str(e))
    st.stop()

# Configuration is valid, hand off to the dashboard
import runpy
runpy.run_path("dashboard/app.py", run_name="__main__")
