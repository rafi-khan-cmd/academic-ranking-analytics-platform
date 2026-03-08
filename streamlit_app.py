"""
Streamlit Cloud entrypoint with validated database configuration.
This is the authoritative entrypoint for cloud deployment.
"""

import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import streamlit early
import streamlit as st

# Deployment marker
print("[DEPLOY MARKER] streamlit_app.py booted - v2")

# Validate database configuration immediately
try:
    from scripts.config import get_db_config
    cfg = get_db_config()
    print(f"[CONFIG] host={cfg['host']} port={cfg['port']} user={cfg['user']}")
except Exception as e:
    st.error("""
    ## ❌ Database Configuration Failed
    
    **Streamlit Cloud did not load valid Supabase credentials.**
    
    Check POSTGRES_* secrets and ensure Session Pooler values are used.
    
    Error: """ + str(e) + """
    
    **To fix:**
    1. Go to Streamlit Cloud → Your app → Settings → Secrets
    2. Verify all 5 secrets are set:
       - POSTGRES_HOST
       - POSTGRES_PORT
       - POSTGRES_DB
       - POSTGRES_USER
       - POSTGRES_PASSWORD
    3. Ensure values match your Supabase Session Pooler connection string
    4. Wait for app to redeploy
    """)
    st.stop()

# Test database connection immediately
try:
    from scripts.database import test_connection
    ok, msg = test_connection()
    print(f"[DB TEST] ok={ok} msg={msg}")
    if not ok:
        st.error("""
        ## ❌ Database Connection Failed
        
        **Streamlit Cloud did not load valid Supabase credentials.**
        
        Check POSTGRES_* secrets and ensure Session Pooler values are used.
        
        Connection error: """ + msg + """
        
        **To fix:**
        1. Verify POSTGRES_HOST matches your Supabase Session Pooler host
        2. Verify POSTGRES_USER includes project ID (e.g., `postgres.PROJECT_ID`)
        3. Verify POSTGRES_PASSWORD matches your Supabase password
        4. Verify POSTGRES_PORT matches Session Pooler port (usually 5432 or 6543)
        5. Wait for app to redeploy
        """)
        st.stop()
except Exception as e:
    st.error("""
    ## ❌ Database Connection Test Failed
    
    **Streamlit Cloud did not load valid Supabase credentials.**
    
    Check POSTGRES_* secrets and ensure Session Pooler values are used.
    
    Error: """ + str(e) + """
    """)
    st.stop()

# Only after successful validation, import and run dashboard/app.py
import runpy
runpy.run_path("dashboard/app.py", run_name="__main__")
