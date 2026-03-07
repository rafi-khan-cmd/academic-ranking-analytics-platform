"""
Subject Rankings page.
Shows subject-specific rankings and analysis.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from dashboard.utils.db_utils import fetch_subjects
from scripts.config import METHODOLOGIES, DEFAULT_YEAR


def render():
    st.header("Subject Rankings")
    st.markdown("""
    Explore how institutions rank within specific academic subjects. 
    Subject-level rankings can differ significantly from overall institutional rankings.
    """)
    
    # Subject selector
    subjects_df = fetch_subjects()
    
    if subjects_df.empty:
        st.info("No subjects available. Subject-level analysis requires additional data processing.")
        st.markdown("""
        **Note:** Subject-level rankings require works data categorized by subject area.
        This feature can be enabled by:
        1. Fetching works data with subject classifications
        2. Aggregating metrics by subject
        3. Computing subject-specific rankings
        """)
        return
    
    # Methodology selector
    methodology = st.sidebar.selectbox("Methodology", list(METHODOLOGIES.keys()), index=0)
    
    # Placeholder for subject rankings
    st.info("""
    **Subject Rankings Feature**
    
    This page will display subject-specific rankings once subject-level data is processed.
    The implementation requires:
    - Works data with subject classifications (e.g., from OpenAlex concepts)
    - Subject-level metric aggregation
    - Subject-specific ranking computation
    
    For now, this page serves as a placeholder demonstrating the intended functionality.
    """)
    
    # Show available subjects
    if not subjects_df.empty:
        st.subheader("Available Subjects")
        st.dataframe(
            subjects_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "subject_id": "ID",
                "subject_name": "Subject Name",
                "subject_group": "Subject Group"
            }
        )
    
    # Example visualization structure
    st.subheader("Example: Subject Ranking Structure")
    
    example_data = {
        "Institution": ["MIT", "Stanford", "Harvard", "Caltech", "Princeton"],
        "Overall Rank": [1, 2, 3, 4, 5],
        "Physics Rank": [1, 3, 5, 2, 4],
        "Computer Science Rank": [2, 1, 4, 3, 5],
        "Mathematics Rank": [1, 2, 3, 4, 5]
    }
    
    example_df = pd.DataFrame(example_data)
    st.dataframe(example_df, use_container_width=True, hide_index=True)
    
    st.markdown("""
    **Key Insight:** Institutions often show different strengths across subjects.
    A top-ranked overall institution may not be the top-ranked in every subject area.
    """)
