"""
Executive Overview page for the dashboard.
Shows high-level KPIs, top institutions, and methodology summaries.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dashboard.utils.db_utils import (
    fetch_top_rankings, fetch_country_summary, 
    fetch_sensitivity_data, fetch_cluster_data
)
from scripts.config import METHODOLOGIES, DEFAULT_YEAR


def render():
    st.header("Executive Overview")
    st.markdown("""
    This dashboard provides a comprehensive view of global academic rankings across multiple 
    methodology profiles. Explore how different weighting schemes affect institutional rankings 
    and discover insights about research performance patterns.
    """)
    
    # Year selector
    year = st.sidebar.selectbox("Year", [DEFAULT_YEAR], index=0)
    methodology = st.sidebar.selectbox("Methodology", list(METHODOLOGIES.keys()), index=0)
    
    # KPI Cards
    st.subheader("Key Performance Indicators")
    
    col1, col2, col3, col4 = st.columns(4)
    
    # Fetch data for KPIs
    top_rankings = fetch_top_rankings(methodology=methodology, limit=100, year=year)
    country_summary = fetch_country_summary(methodology=methodology, year=year)
    
    with col1:
        st.metric("Total Institutions", len(top_rankings))
    
    with col2:
        st.metric("Countries Represented", len(country_summary))
    
    with col3:
        avg_score = top_rankings["overall_score"].mean() if not top_rankings.empty else 0
        st.metric("Average Score", f"{avg_score:.3f}")
    
    with col4:
        top_score = top_rankings["overall_score"].max() if not top_rankings.empty else 0
        st.metric("Top Score", f"{top_score:.3f}")
    
    st.markdown("---")
    
    # Top Institutions Chart
    st.subheader(f"Top 20 Institutions - {methodology}")
    
    if not top_rankings.empty:
        top_20 = top_rankings.head(20)
        
        fig = px.bar(
            top_20,
            x="overall_score",
            y="institution_name",
            orientation="h",
            color="overall_score",
            color_continuous_scale="Blues",
            labels={"overall_score": "Overall Score", "institution_name": "Institution"},
            title="Top 20 Institutions by Overall Score"
        )
        fig.update_layout(height=600, yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No ranking data available. Please run the data pipeline first.")
    
    # Country Performance
    st.subheader("Country-Level Performance")
    
    if not country_summary.empty:
        country_summary_sorted = country_summary.head(15).sort_values("avg_score", ascending=True)
        
        fig = px.bar(
            country_summary_sorted,
            x="avg_score",
            y="country",
            orientation="h",
            color="institution_count",
            color_continuous_scale="Viridis",
            labels={
                "avg_score": "Average Score",
                "country": "Country",
                "institution_count": "Institutions"
            },
            title="Top 15 Countries by Average Score"
        )
        fig.update_layout(height=500, yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No country summary data available.")
    
    # Methodology Summary
    st.subheader("Methodology Profiles")
    
    methodology_df = pd.DataFrame([
        {
            "Methodology": name,
            "Publication": weights["publication_weight"],
            "Citation": weights["citation_weight"],
            "Collaboration": weights["collaboration_weight"],
            "Quality": weights["quality_weight"],
            "Subject Strength": weights["subject_strength_weight"],
            "Productivity": weights["productivity_weight"]
        }
        for name, weights in METHODOLOGIES.items()
    ])
    
    st.dataframe(methodology_df, use_container_width=True, hide_index=True)
    
    # Key Insights
    st.subheader("Key Insights")
    
    insights = [
        f"**{methodology}** emphasizes {get_primary_emphasis(METHODOLOGIES[methodology])}",
        f"The top institution has a score of {top_rankings['overall_score'].max():.3f}" if not top_rankings.empty else "No data available",
        f"Average institutional score is {avg_score:.3f}" if not top_rankings.empty else "No data available",
        f"{len(country_summary)} countries are represented in the rankings"
    ]
    
    for insight in insights:
        st.markdown(f"- {insight}")


def get_primary_emphasis(weights: dict) -> str:
    """Get the primary emphasis of a methodology."""
    max_weight = max(weights.items(), key=lambda x: x[1] if "weight" in x[0] else 0)
    emphasis_map = {
        "publication_weight": "publication volume",
        "citation_weight": "citation impact",
        "collaboration_weight": "international collaboration",
        "quality_weight": "research quality",
        "subject_strength_weight": "subject-specific excellence",
        "productivity_weight": "research productivity"
    }
    return emphasis_map.get(max_weight[0], "balanced indicators")
