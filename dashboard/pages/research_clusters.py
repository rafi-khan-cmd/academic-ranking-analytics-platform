"""
Research Clusters page.
Shows institution clustering analysis and cluster profiles.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from dashboard.utils.db_utils import fetch_cluster_data, fetch_all_institutions
from scripts.advanced_analytics import compute_institution_clusters, save_clusters_to_db
from scripts.config import DEFAULT_YEAR


def render():
    st.header("Research Clusters")
    st.markdown("""
    Explore how institutions cluster into distinct research profiles based on their 
    indicator patterns. Clustering reveals different institutional archetypes.
    """)
    
    # Cluster computation controls
    st.sidebar.subheader("Cluster Settings")
    n_clusters = st.sidebar.slider("Number of Clusters", min_value=2, max_value=8, value=4)
    
    if st.sidebar.button("Recompute Clusters"):
        with st.spinner("Computing clusters..."):
            clusters = compute_institution_clusters(n_clusters=n_clusters, year=DEFAULT_YEAR)
            if clusters:
                save_clusters_to_db(clusters, n_clusters=n_clusters)
                st.sidebar.success("Clusters computed and saved!")
    
    # Fetch cluster data
    cluster_df = fetch_cluster_data()
    
    if cluster_df.empty:
        st.info("""
        No cluster data available. Click 'Recompute Clusters' in the sidebar to generate 
        cluster assignments based on institutional indicator profiles.
        """)
        return
    
    # Cluster Summary
    st.subheader("Cluster Summary")
    
    cluster_summary = cluster_df.groupby("cluster_label").agg({
        "institution_name": "count",
        "country": lambda x: x.nunique()
    }).reset_index()
    cluster_summary.columns = ["Cluster", "Institution Count", "Country Count"]
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig = px.bar(
            cluster_summary,
            x="Cluster",
            y="Institution Count",
            color="Cluster",
            labels={"Institution Count": "Number of Institutions"},
            title="Institutions per Cluster"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.dataframe(cluster_summary, use_container_width=True, hide_index=True)
    
    # Cluster Descriptions
    st.subheader("Cluster Profiles")
    
    cluster_descriptions = {
        "High-Impact Elite": """
        Institutions with exceptional citation impact and research quality. 
        These institutions produce highly-cited research and maintain strong 
        quality metrics across indicators.
        """,
        "High-Volume Output": """
        Institutions with high publication volume. These institutions produce 
        a large number of publications, emphasizing research output.
        """,
        "Collaboration-Driven": """
        Institutions with strong international collaboration. These institutions 
        excel in collaborative research and international partnerships.
        """,
        "Subject Specialist": """
        Institutions with subject-specific excellence. These institutions show 
        particular strength in specific academic domains.
        """
    }
    
    for cluster_label in cluster_df["cluster_label"].unique():
        with st.expander(f"**{cluster_label}**"):
            desc = cluster_descriptions.get(cluster_label, "Cluster profile description.")
            st.markdown(desc)
            
            cluster_institutions = cluster_df[cluster_df["cluster_label"] == cluster_label]
            st.markdown(f"**Institutions in this cluster:** {len(cluster_institutions)}")
            
            # Show sample institutions
            sample = cluster_institutions[["institution_name", "country"]].head(10)
            st.dataframe(sample, use_container_width=True, hide_index=True)
    
    # Cluster by Country
    st.subheader("Cluster Distribution by Country")
    
    country_cluster = pd.crosstab(cluster_df["country"], cluster_df["cluster_label"])
    
    if not country_cluster.empty:
        fig = px.bar(
            country_cluster.reset_index().melt(id_vars="country", var_name="Cluster", value_name="Count"),
            x="country",
            y="Count",
            color="Cluster",
            labels={"country": "Country", "Count": "Number of Institutions"},
            title="Cluster Distribution by Country"
        )
        fig.update_xaxes(tickangle=45)
        st.plotly_chart(fig, use_container_width=True)
    
    # Institution Search
    st.subheader("Find Institution Cluster")
    
    institutions_df = fetch_all_institutions()
    institution_options = institutions_df["institution_name"].tolist()
    selected_inst = st.selectbox("Select Institution", [None] + institution_options)
    
    if selected_inst:
        inst_cluster = cluster_df[cluster_df["institution_name"] == selected_inst]
        if not inst_cluster.empty:
            cluster_info = inst_cluster.iloc[0]
            st.success(f"**{selected_inst}** belongs to the **{cluster_info['cluster_label']}** cluster.")
            st.markdown(f"**Description:** {cluster_info.get('cluster_description', 'N/A')}")
        else:
            st.info(f"No cluster assignment found for {selected_inst}")
