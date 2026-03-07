"""
Institution Explorer page.
Allows detailed exploration of individual institutions.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dashboard.utils.db_utils import (
    fetch_institution_details, fetch_institution_rankings,
    fetch_all_institutions
)
from scripts.config import DEFAULT_YEAR


def render():
    st.header("Institution Explorer")
    st.markdown("""
    Explore detailed profiles of individual institutions, including indicator breakdowns,
    rankings across methodologies, and institutional characteristics.
    """)
    
    # Institution selector
    institutions_df = fetch_all_institutions()
    
    if institutions_df.empty:
        st.info("No institutions available. Please run the data pipeline first.")
        return
    
    institution_options = institutions_df["institution_name"].tolist()
    selected_institution = st.selectbox("Select Institution", institution_options)
    
    if not selected_institution:
        return
    
    # Fetch institution details
    details = fetch_institution_details(selected_institution, year=DEFAULT_YEAR)
    
    if details.empty:
        st.warning(f"No data found for {selected_institution}")
        return
    
    inst_data = details.iloc[0]
    institution_id = inst_data["institution_id"]
    
    # Institution Header
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader(inst_data["institution_name"])
        st.markdown(f"**Country:** {inst_data.get('country', 'N/A')}")
        if inst_data.get('region'):
            st.markdown(f"**Region:** {inst_data.get('region')}")
    
    with col2:
        st.metric("Institution ID", institution_id)
    
    st.markdown("---")
    
    # Indicator Radar Chart
    st.subheader("Indicator Profile")
    
    indicator_scores = {
        "Publication": inst_data.get("publication_score", 0),
        "Citation": inst_data.get("citation_score", 0),
        "Collaboration": inst_data.get("collaboration_score", 0),
        "Quality": inst_data.get("quality_score", 0),
        "Subject Strength": inst_data.get("subject_strength_score", 0),
        "Productivity": inst_data.get("productivity_score", 0)
    }
    
    # Create radar chart
    fig = go.Figure()
    
    fig.add_trace(go.Scatterpolar(
        r=list(indicator_scores.values()),
        theta=list(indicator_scores.keys()),
        fill='toself',
        name='Normalized Scores'
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 1]
            )),
        showlegend=True,
        title="Indicator Profile (Normalized Scores)"
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Raw vs Normalized Metrics
    st.subheader("Raw Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Publications", int(inst_data.get("publication_count", 0)))
        st.metric("Citations", int(inst_data.get("citation_count", 0)))
    
    with col2:
        st.metric("Citations/Paper", f"{inst_data.get('citations_per_paper', 0):.2f}")
        st.metric("Collaboration Rate", f"{inst_data.get('international_collaboration_rate', 0):.2%}")
    
    with col3:
        st.metric("Quality Proxy", f"{inst_data.get('quality_proxy', 0):.2f}")
        st.metric("Productivity Proxy", f"{inst_data.get('productivity_proxy', 0):.2f}")
    
    with col4:
        st.metric("Publication Score", f"{inst_data.get('publication_score', 0):.3f}")
        st.metric("Citation Score", f"{inst_data.get('citation_score', 0):.3f}")
    
    # Rankings Across Methodologies
    st.subheader("Rankings Across Methodologies")
    
    rankings = fetch_institution_rankings(institution_id, year=DEFAULT_YEAR)
    
    if not rankings.empty:
        fig = px.bar(
            rankings,
            x="methodology_name",
            y="rank_position",
            color="overall_score",
            color_continuous_scale="RdYlGn_r",
            labels={
                "methodology_name": "Methodology",
                "rank_position": "Rank Position",
                "overall_score": "Overall Score"
            },
            title="Rank Position by Methodology (Lower is Better)"
        )
        fig.update_layout(yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig, use_container_width=True)
        
        # Rankings table
        st.dataframe(
            rankings[["methodology_name", "rank_position", "overall_score"]],
            use_container_width=True,
            hide_index=True,
            column_config={
                "methodology_name": "Methodology",
                "rank_position": "Rank",
                "overall_score": "Score"
            }
        )
    else:
        st.info("No ranking data available for this institution.")
    
    # Institution Summary
    st.subheader("Institution Summary")
    
    summary_text = f"""
    **{inst_data['institution_name']}** is located in {inst_data.get('country', 'N/A')}.
    
    The institution shows:
    - **Publication Score:** {inst_data.get('publication_score', 0):.3f}
    - **Citation Score:** {inst_data.get('citation_score', 0):.3f}
    - **Quality Score:** {inst_data.get('quality_score', 0):.3f}
    - **Collaboration Score:** {inst_data.get('collaboration_score', 0):.3f}
    
    With {int(inst_data.get('publication_count', 0))} publications and 
    {int(inst_data.get('citation_count', 0))} total citations, the institution demonstrates
    {'strong' if inst_data.get('citation_score', 0) > 0.5 else 'moderate'} research impact.
    """
    
    st.markdown(summary_text)
