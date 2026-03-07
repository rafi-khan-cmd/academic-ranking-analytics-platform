"""
Indicator Analytics page.
Shows correlation analysis, feature importance, and indicator relationships.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from sqlalchemy import text
from scripts.database import create_db_engine
from scripts.advanced_analytics import compute_feature_importance
from scripts.config import DEFAULT_YEAR


def render():
    st.header("Indicator Analytics")
    st.markdown("""
    Analyze relationships between ranking indicators, understand feature importance,
    and explore how different metrics correlate with overall performance.
    """)
    
    # Fetch normalized metrics for analysis
    engine = create_db_engine()
    
    query = text("""
        SELECT 
            nm.publication_score,
            nm.citation_score,
            nm.collaboration_score,
            nm.quality_score,
            nm.subject_strength_score,
            nm.productivity_score,
            r.overall_score
        FROM normalized_metrics nm
        JOIN ranking_results r ON 
            nm.institution_id = r.institution_id 
            AND nm.year = r.year
        WHERE nm.year = :year
          AND r.methodology_name = 'Balanced Model'
          AND nm.subject_id IS NULL
    """)
    
    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params={"year": DEFAULT_YEAR})
    
    if df.empty:
        st.info("No indicator data available. Please run the data pipeline first.")
        return
    
    # Correlation Heatmap
    st.subheader("Indicator Correlation Matrix")
    
    indicator_cols = [
        "publication_score", "citation_score", "collaboration_score",
        "quality_score", "subject_strength_score", "productivity_score", "overall_score"
    ]
    
    corr_matrix = df[indicator_cols].corr()
    
    fig = px.imshow(
        corr_matrix,
        labels=dict(x="Indicator", y="Indicator", color="Correlation"),
        x=corr_matrix.columns,
        y=corr_matrix.columns,
        color_continuous_scale="RdBu",
        aspect="auto",
        title="Correlation Matrix of Ranking Indicators"
    )
    fig.update_layout(height=600)
    st.plotly_chart(fig, use_container_width=True)
    
    # Feature Importance
    st.subheader("Feature Importance Analysis")
    st.markdown("""
    Feature importance shows which indicators are most predictive of overall ranking scores.
    Computed using Random Forest regression.
    """)
    
    if st.button("Compute Feature Importance"):
        with st.spinner("Computing feature importance..."):
            importance = compute_feature_importance(year=DEFAULT_YEAR)
            
            if importance:
                importance_df = pd.DataFrame([
                    {"Indicator": k.replace("_score", "").title(), "Importance": v}
                    for k, v in importance.items()
                ]).sort_values("Importance", ascending=False)
                
                fig = px.bar(
                    importance_df,
                    x="Importance",
                    y="Indicator",
                    orientation="h",
                    color="Importance",
                    color_continuous_scale="Blues",
                    labels={"Importance": "Feature Importance Score"},
                    title="Feature Importance for Overall Score Prediction"
                )
                fig.update_layout(height=400, yaxis={'categoryorder': 'total ascending'})
                st.plotly_chart(fig, use_container_width=True)
                
                st.dataframe(importance_df, use_container_width=True, hide_index=True)
    
    # Scatter Plots
    st.subheader("Indicator Relationships")
    
    col1, col2 = st.columns(2)
    
    with col1:
        x_indicator = st.selectbox(
            "X-Axis Indicator",
            ["publication_score", "citation_score", "collaboration_score", 
             "quality_score", "productivity_score"],
            index=1
        )
    
    with col2:
        y_indicator = st.selectbox(
            "Y-Axis Indicator",
            ["publication_score", "citation_score", "collaboration_score",
             "quality_score", "productivity_score", "overall_score"],
            index=5
        )
    
    fig = px.scatter(
        df,
        x=x_indicator,
        y=y_indicator,
        color="overall_score",
        color_continuous_scale="Viridis",
        labels={
            x_indicator: x_indicator.replace("_", " ").title(),
            y_indicator: y_indicator.replace("_", " ").title(),
            "overall_score": "Overall Score"
        },
        title=f"{x_indicator.replace('_', ' ').title()} vs {y_indicator.replace('_', ' ').title()}"
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Distribution Analysis
    st.subheader("Indicator Distributions")
    
    selected_indicator = st.selectbox(
        "Select Indicator for Distribution Analysis",
        ["publication_score", "citation_score", "collaboration_score",
         "quality_score", "productivity_score", "overall_score"],
        index=0
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig_hist = px.histogram(
            df,
            x=selected_indicator,
            nbins=30,
            labels={selected_indicator: selected_indicator.replace("_", " ").title()},
            title=f"Distribution of {selected_indicator.replace('_', ' ').title()}"
        )
        st.plotly_chart(fig_hist, use_container_width=True)
    
    with col2:
        fig_box = px.box(
            df,
            y=selected_indicator,
            labels={selected_indicator: selected_indicator.replace("_", " ").title()},
            title=f"Box Plot of {selected_indicator.replace('_', ' ').title()}"
        )
        st.plotly_chart(fig_box, use_container_width=True)
    
    # Summary Statistics
    st.subheader("Summary Statistics")
    st.dataframe(
        df[indicator_cols].describe(),
        use_container_width=True
    )
