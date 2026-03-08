"""
Academic Rankings Intelligence Platform
Main Streamlit application entry point.
"""

import streamlit as st
import sys
from pathlib import Path
import logging

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import config and database modules explicitly
from scripts.config import get_config_value
from scripts.database import create_db_engine

# Startup validation: Check for required database credentials
def validate_database_credentials():
    """Validate that all required database credentials are present.
    
    Raises:
        SystemExit: If any credential is missing, stops the app with clear error message.
    """
    required_keys = [
        "POSTGRES_HOST",
        "POSTGRES_PORT", 
        "POSTGRES_DB",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD"
    ]
    
    missing_keys = []
    credentials = {}
    
    for key in required_keys:
        value = get_config_value(key)
        if not value:
            missing_keys.append(key)
        else:
            credentials[key] = value
    
    if missing_keys:
        # Log error (safe values only)
        logger.error(f"Missing database credentials: {', '.join(missing_keys)}")
        
        # Show clear error in UI and stop the app
        st.error("""
        ## ❌ Database Configuration Error
        
        **Database credentials were not loaded from Streamlit Cloud secrets.**
        
        Missing credentials: """ + ", ".join(missing_keys) + """
        
        **To fix:**
        1. Go to Streamlit Cloud → Your app → Settings → Secrets
        2. Add the following secrets:
           - POSTGRES_HOST
           - POSTGRES_PORT
           - POSTGRES_DB
           - POSTGRES_USER
           - POSTGRES_PASSWORD
        3. Verify the app file is `dashboard/app.py` and POSTGRES_* secrets are set.
        4. Wait for the app to redeploy
        """)
        st.stop()
    
    # Startup debug log (server logs only, not UI) - safe values only
    host = credentials.get("POSTGRES_HOST", "NOT SET")
    port = credentials.get("POSTGRES_PORT", "NOT SET")
    user = credentials.get("POSTGRES_USER", "NOT SET")
    logger.info(f"[STARTUP] Database credentials loaded: host={host} port={port} user={user}")
    
    # Additional validation: check for localhost
    if host == "localhost":
        logger.error("Database host is localhost - credentials not loaded correctly")
        st.error("""
        ## ❌ Database Configuration Error
        
        **Database host incorrectly set to localhost.**
        
        Supabase credentials were not loaded from Streamlit Cloud secrets.
        
        **To fix:**
        1. Verify POSTGRES_HOST in Streamlit Cloud secrets is set to your Supabase host
        2. Verify the app file is `dashboard/app.py` and POSTGRES_* secrets are set.
        3. Wait for the app to redeploy
        """)
        st.stop()
    
    return credentials

# Validate credentials at startup
try:
    db_credentials = validate_database_credentials()
except Exception as e:
    logger.error(f"Credential validation failed: {e}")
    st.error(f"""
    ## ❌ Database Configuration Error
    
    **Failed to load database credentials: {str(e)}**
    
    Verify the app file is `dashboard/app.py` and POSTGRES_* secrets are set in Streamlit Cloud.
    """)
    st.stop()

# Check database availability
try:
    from dashboard.utils.db_utils import check_database_available
    db_available, db_message = check_database_available()
except Exception as e:
    db_available = False
    db_message = f"Database check failed: {str(e)}"

# Page configuration
st.set_page_config(
    page_title="Academic Rankings Intelligence Platform",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional styling
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .subtitle {
        font-size: 1.2rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    </style>
""", unsafe_allow_html=True)

# Main header
st.markdown('<h1 class="main-header">Academic Rankings Intelligence Platform</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">A Python, PostgreSQL, and Streamlit analytics platform for modeling, simulating, and explaining global university ranking methodologies</p>', unsafe_allow_html=True)

# Database status warning
if not db_available:
    st.warning(f"⚠️ {db_message}")
    st.info("""
    **To get started:**
    1. Set up a PostgreSQL database (local or cloud)
    2. Configure database credentials in Streamlit Cloud secrets
    3. Run the data pipeline: `python scripts/run_pipeline.py --institutions 200`
    4. Or use sample data: `python scripts/create_sample_data.py`
    
    See `NEXT_STEPS.md` for detailed instructions.
    """)

# Sidebar navigation
st.sidebar.title("Navigation")
st.sidebar.markdown("---")

# Page selection
page = st.sidebar.radio(
    "Select Page",
    [
        "Executive Overview",
        "Global Rankings",
        "Institution Explorer",
        "Methodology Simulator",
        "Subject Rankings",
        "Indicator Analytics",
        "Research Clusters"
    ]
)

# Route to appropriate page
if page == "Executive Overview":
    from dashboard.pages import executive_overview
    executive_overview.render()
elif page == "Global Rankings":
    from dashboard.pages import global_rankings
    global_rankings.render()
elif page == "Institution Explorer":
    from dashboard.pages import institution_explorer
    institution_explorer.render()
elif page == "Methodology Simulator":
    from dashboard.pages import methodology_simulator
    methodology_simulator.render()
elif page == "Subject Rankings":
    from dashboard.pages import subject_rankings
    subject_rankings.render()
elif page == "Indicator Analytics":
    from dashboard.pages import indicator_analytics
    indicator_analytics.render()
elif page == "Research Clusters":
    from dashboard.pages import research_clusters
    research_clusters.render()

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("**Academic Rankings Intelligence Platform**")
st.sidebar.markdown("Built with Python, PostgreSQL, and Streamlit")
