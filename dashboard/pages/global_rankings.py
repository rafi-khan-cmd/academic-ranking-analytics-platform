"""
Global Rankings page.
Shows sortable ranking tables with filters.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from dashboard.utils.db_utils import fetch_top_rankings, fetch_all_institutions
from scripts.config import METHODOLOGIES, DEFAULT_YEAR


def render():
    st.header("Global Rankings")
    st.markdown("""
    Explore comprehensive global rankings across different methodology profiles. 
    Filter by methodology, country, and year to analyze institutional performance.
    """)
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        methodology = st.selectbox("Methodology", list(METHODOLOGIES.keys()), index=0)
    
    with col2:
        year = st.selectbox("Year", [DEFAULT_YEAR], index=0)
    
    with col3:
        all_countries = fetch_all_institutions()["country"].dropna().unique()
        country_filter = st.selectbox("Country (Optional)", [None] + sorted(all_countries.tolist()))
    
    # Fetch rankings
    rankings = fetch_top_rankings(
        methodology=methodology,
        limit=500,
        year=year,
        country=country_filter
    )
    
    if rankings.empty:
        st.info("No ranking data available. Please run the data pipeline first.")
        return
    
    # Display summary stats
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Institutions", len(rankings))
    with col2:
        st.metric("Average Score", f"{rankings['overall_score'].mean():.3f}")
    with col3:
        st.metric("Score Range", f"{rankings['overall_score'].min():.3f} - {rankings['overall_score'].max():.3f}")
    
    st.markdown("---")
    
    # Ranking Table
    st.subheader("Ranking Table")
    
    # Prepare display dataframe
    display_df = rankings[["rank_position", "institution_name", "country", "overall_score"]].copy()
    display_df.columns = ["Rank", "Institution", "Country", "Score"]
    
    # Add search
    search_term = st.text_input("Search institutions", "")
    if search_term:
        display_df = display_df[
            display_df["Institution"].str.contains(search_term, case=False, na=False)
        ]
    
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        height=600
    )
    
    # Score Distribution
    st.subheader("Score Distribution")
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig_hist = px.histogram(
            rankings,
            x="overall_score",
            nbins=30,
            labels={"overall_score": "Overall Score", "count": "Number of Institutions"},
            title="Distribution of Overall Scores"
        )
        st.plotly_chart(fig_hist, use_container_width=True)
    
    with col2:
        fig_box = px.box(
            rankings,
            y="overall_score",
            labels={"overall_score": "Overall Score"},
            title="Score Distribution by Quartiles"
        )
        st.plotly_chart(fig_box, use_container_width=True)
    
    # Top Movers (if comparing methodologies)
    if len(METHODOLOGIES) > 1:
        st.subheader("Methodology Comparison")
        st.markdown("Compare how institutions rank across different methodologies.")
        
        methodology_comparison = st.multiselect(
            "Select methodologies to compare",
            list(METHODOLOGIES.keys()),
            default=[list(METHODOLOGIES.keys())[0]]
        )
        
        if len(methodology_comparison) > 1:
            comparison_data = []
            for method in methodology_comparison:
                method_rankings = fetch_top_rankings(methodology=method, limit=100, year=year)
                for _, row in method_rankings.iterrows():
                    comparison_data.append({
                        "Institution": row["institution_name"],
                        "Methodology": method,
                        "Rank": row["rank_position"],
                        "Score": row["overall_score"]
                    })
            
            if comparison_data:
                comparison_df = pd.DataFrame(comparison_data)
                
                # Pivot for comparison
                pivot_df = comparison_df.pivot_table(
                    index="Institution",
                    columns="Methodology",
                    values="Rank",
                    aggfunc="first"
                ).reset_index()
                
                st.dataframe(pivot_df, use_container_width=True, hide_index=True)
