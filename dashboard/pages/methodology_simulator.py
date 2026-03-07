"""
Methodology Simulator page.
Interactive tool for exploring custom methodology weights.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from scripts.ranking_simulator import simulate_rankings, compare_rankings, get_baseline_rankings
from scripts.config import METHODOLOGIES, DEFAULT_YEAR
from dashboard.utils.db_utils import fetch_all_institutions


def render():
    st.header("Methodology Simulator")
    st.markdown("""
    Explore how different indicator weights affect institutional rankings. 
    Adjust the sliders below to create custom methodology profiles and see 
    how rankings change in real-time.
    """)
    
    # Baseline methodology selector
    baseline_method = st.sidebar.selectbox(
        "Baseline Methodology",
        list(METHODOLOGIES.keys()),
        index=0,
        help="Select a baseline methodology to compare against"
    )
    
    # Weight sliders
    st.subheader("Custom Methodology Weights")
    st.markdown("Adjust the weights for each indicator. Weights should sum to 1.0.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        pub_weight = st.slider(
            "Publication Weight",
            min_value=0.0,
            max_value=1.0,
            value=0.2,
            step=0.05,
            help="Weight for publication volume indicator"
        )
        
        cite_weight = st.slider(
            "Citation Weight",
            min_value=0.0,
            max_value=1.0,
            value=0.2,
            step=0.05,
            help="Weight for citation impact indicator"
        )
        
        collab_weight = st.slider(
            "Collaboration Weight",
            min_value=0.0,
            max_value=1.0,
            value=0.2,
            step=0.05,
            help="Weight for international collaboration indicator"
        )
    
    with col2:
        quality_weight = st.slider(
            "Quality Weight",
            min_value=0.0,
            max_value=1.0,
            value=0.2,
            step=0.05,
            help="Weight for research quality indicator"
        )
        
        subject_weight = st.slider(
            "Subject Strength Weight",
            min_value=0.0,
            max_value=1.0,
            value=0.1,
            step=0.05,
            help="Weight for subject-specific strength indicator"
        )
        
        prod_weight = st.slider(
            "Productivity Weight",
            min_value=0.0,
            max_value=1.0,
            value=0.1,
            step=0.05,
            help="Weight for research productivity indicator"
        )
    
    # Calculate total weight
    total_weight = pub_weight + cite_weight + collab_weight + quality_weight + subject_weight + prod_weight
    
    # Weight validation
    if abs(total_weight - 1.0) > 0.01:
        st.warning(f"⚠️ Weights sum to {total_weight:.2f}. Please adjust to sum to 1.0 for accurate rankings.")
        normalize = st.checkbox("Normalize weights automatically", value=False)
        if normalize:
            total = total_weight
            pub_weight = pub_weight / total
            cite_weight = cite_weight / total
            collab_weight = collab_weight / total
            quality_weight = quality_weight / total
            subject_weight = subject_weight / total
            prod_weight = prod_weight / total
            st.success(f"Weights normalized. New total: {pub_weight + cite_weight + collab_weight + quality_weight + subject_weight + prod_weight:.2f}")
    else:
        st.success(f"✓ Weights sum to {total_weight:.2f}")
    
    # Custom weights dictionary
    custom_weights = {
        "publication_weight": pub_weight,
        "citation_weight": cite_weight,
        "collaboration_weight": collab_weight,
        "quality_weight": quality_weight,
        "subject_strength_weight": subject_weight,
        "productivity_weight": prod_weight
    }
    
    # Country filter (optional)
    institutions_df = fetch_all_institutions()
    all_countries = [None] + sorted(institutions_df["country"].dropna().unique().tolist())
    country_filter = st.selectbox("Filter by Country (Optional)", all_countries)
    
    # Simulate rankings
    if st.button("Calculate Rankings", type="primary"):
        with st.spinner("Computing rankings..."):
            # Get baseline
            baseline = get_baseline_rankings(baseline_method, year=DEFAULT_YEAR)
            
            # Simulate with custom weights
            simulated = simulate_rankings(
                custom_weights=custom_weights,
                year=DEFAULT_YEAR,
                country_filter=country_filter
            )
            
            # Compare
            comparison = compare_rankings(baseline, simulated)
            
            # Store in session state
            st.session_state['simulated_rankings'] = simulated
            st.session_state['comparison'] = comparison
            st.session_state['baseline'] = baseline
    
    # Display results if available
    if 'simulated_rankings' in st.session_state:
        st.markdown("---")
        
        # Top Rankings
        st.subheader("Top 20 Institutions (Custom Methodology)")
        
        top_20 = pd.DataFrame(st.session_state['simulated_rankings'][:20])
        top_20_display = top_20[["rank_position", "institution_name", "country", "overall_score"]].copy()
        top_20_display.columns = ["Rank", "Institution", "Country", "Score"]
        
        fig = px.bar(
            top_20,
            x="overall_score",
            y="institution_name",
            orientation="h",
            color="overall_score",
            color_continuous_scale="Blues",
            labels={"overall_score": "Overall Score", "institution_name": "Institution"},
            title="Top 20 Institutions"
        )
        fig.update_layout(height=600, yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig, use_container_width=True)
        
        # Rank Movement
        st.subheader("Rank Movement Analysis")
        st.markdown("Compare how institutions moved compared to the baseline methodology.")
        
        comparison_df = pd.DataFrame(st.session_state['comparison'])
        
        if not comparison_df.empty:
            # Biggest movers
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Biggest Winners (Moved Up)**")
                winners = comparison_df.nlargest(10, "rank_change")[
                    ["institution_name", "country", "old_rank", "new_rank", "rank_change"]
                ]
                winners.columns = ["Institution", "Country", "Old Rank", "New Rank", "Change"]
                st.dataframe(winners, use_container_width=True, hide_index=True)
            
            with col2:
                st.markdown("**Biggest Losers (Moved Down)**")
                losers = comparison_df.nsmallest(10, "rank_change")[
                    ["institution_name", "country", "old_rank", "new_rank", "rank_change"]
                ]
                losers.columns = ["Institution", "Country", "Old Rank", "New Rank", "Change"]
                st.dataframe(losers, use_container_width=True, hide_index=True)
            
            # Movement visualization
            st.subheader("Rank Change Distribution")
            fig = px.histogram(
                comparison_df,
                x="rank_change",
                nbins=30,
                labels={"rank_change": "Rank Change (Positive = Moved Up)", "count": "Number of Institutions"},
                title="Distribution of Rank Changes"
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Methodology comparison explanation
            st.subheader("Methodology Comparison")
            st.markdown(f"""
            **Baseline:** {baseline_method}
            **Custom Methodology:** Publication={pub_weight:.2f}, Citation={cite_weight:.2f}, 
            Collaboration={collab_weight:.2f}, Quality={quality_weight:.2f}, 
            Subject Strength={subject_weight:.2f}, Productivity={prod_weight:.2f}
            
            The custom methodology {'emphasizes' if max(custom_weights.values()) > 0.3 else 'balances'} 
            {max(custom_weights, key=custom_weights.get).replace('_weight', '').title()} indicators.
            """)
