"""
Academic Rankings Intelligence Platform
Main Streamlit application entry point.

Note: Database configuration and connection validation is performed
in streamlit_app.py before this module is loaded.
"""

print("[APP] dashboard/app.py loaded")

import streamlit as st
import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Check database availability for UI display (non-blocking, for status messages only)
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
