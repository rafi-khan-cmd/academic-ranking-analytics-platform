"""
Advanced analytics module.
Implements feature importance, clustering, and sensitivity analysis.
"""

import logging
from typing import List, Dict, Tuple
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sqlalchemy import text

from scripts.database import create_db_engine
from scripts.config import DEFAULT_YEAR

logger = logging.getLogger(__name__)


def compute_feature_importance(year: int = DEFAULT_YEAR) -> Dict[str, float]:
    """
    Compute feature importance using Random Forest to understand
    which indicators are most associated with ranking scores.
    """
    logger.info("Computing feature importance...")
    
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
        df = pd.read_sql(query, conn, params={"year": year})
    
    if df.empty:
        logger.warning("No data found for feature importance analysis")
        return {}
    
    # Prepare features and target
    feature_cols = [
        "publication_score", "citation_score", "collaboration_score",
        "quality_score", "subject_strength_score", "productivity_score"
    ]
    
    X = df[feature_cols].fillna(0)
    y = df["overall_score"].fillna(0)
    
    # Train Random Forest
    rf = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
    rf.fit(X, y)
    
    # Extract feature importance
    importance_dict = {
        feature: float(importance)
        for feature, importance in zip(feature_cols, rf.feature_importances_)
    }
    
    logger.info("Feature importance computed")
    return importance_dict


def compute_institution_clusters(n_clusters: int = 4, year: int = DEFAULT_YEAR) -> List[Dict]:
    """
    Cluster institutions into profiles using KMeans.
    
    Args:
        n_clusters: Number of clusters
        year: Year for clustering
    
    Returns:
        List of cluster assignments
    """
    logger.info(f"Computing institution clusters (n_clusters={n_clusters})...")
    
    engine = create_db_engine()
    
    query = text("""
        SELECT 
            nm.institution_id,
            i.institution_name,
            i.country,
            nm.publication_score,
            nm.citation_score,
            nm.collaboration_score,
            nm.quality_score,
            nm.subject_strength_score,
            nm.productivity_score
        FROM normalized_metrics nm
        JOIN institutions i ON nm.institution_id = i.institution_id
        WHERE nm.year = :year
          AND nm.subject_id IS NULL
    """)
    
    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params={"year": year})
    
    if df.empty:
        logger.warning("No data found for clustering")
        return []
    
    # Prepare features
    feature_cols = [
        "publication_score", "citation_score", "collaboration_score",
        "quality_score", "subject_strength_score", "productivity_score"
    ]
    
    X = df[feature_cols].fillna(0)
    
    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Perform clustering
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    cluster_labels = kmeans.fit_predict(X_scaled)
    
    # Create cluster descriptions based on centroids
    cluster_descriptions = []
    for i in range(n_clusters):
        centroid = kmeans.cluster_centers_[i]
        # Find dominant features
        feature_values = {
            "publication": centroid[0],
            "citation": centroid[1],
            "collaboration": centroid[2],
            "quality": centroid[3],
            "subject_strength": centroid[4],
            "productivity": centroid[5]
        }
        max_feature = max(feature_values, key=feature_values.get)
        
        descriptions = {
            0: "High-Impact Elite",
            1: "High-Volume Output",
            2: "Collaboration-Driven",
            3: "Subject Specialist"
        }
        
        cluster_descriptions.append(
            descriptions.get(i, f"Cluster {i+1}") if i < len(descriptions) else f"Cluster {i+1}"
        )
    
    # Create results
    results = []
    for idx, row in df.iterrows():
        cluster_label = cluster_descriptions[cluster_labels[idx]]
        results.append({
            "institution_id": int(row["institution_id"]),
            "institution_name": row["institution_name"],
            "country": row["country"],
            "cluster_label": cluster_label,
            "cluster_id": int(cluster_labels[idx])
        })
    
    logger.info(f"Computed {n_clusters} clusters for {len(results)} institutions")
    return results


def save_clusters_to_db(clusters: List[Dict], method: str = "kmeans", n_clusters: int = 4) -> None:
    """Save cluster assignments to database."""
    logger.info(f"Saving {len(clusters)} cluster assignments...")
    
    engine = create_db_engine()
    
    with engine.connect() as conn:
        for cluster in clusters:
            # Get cluster description
            cluster_label = cluster["cluster_label"]
            descriptions = {
                "High-Impact Elite": "Institutions with exceptional citation impact and research quality",
                "High-Volume Output": "Institutions with high publication volume",
                "Collaboration-Driven": "Institutions with strong international collaboration",
                "Subject Specialist": "Institutions with subject-specific excellence"
            }
            description = descriptions.get(cluster_label, f"{cluster_label} profile")
            
            check_query = text("""
                SELECT cluster_id FROM institution_clusters 
                WHERE institution_id = :inst_id AND cluster_method = :method
            """)
            result = conn.execute(
                check_query,
                {"inst_id": cluster["institution_id"], "method": method}
            ).fetchone()
            
            if result:
                update_query = text("""
                    UPDATE institution_clusters 
                    SET cluster_label = :label, cluster_description = :desc, n_clusters = :n
                    WHERE cluster_id = :cluster_id
                """)
                conn.execute(
                    update_query,
                    {
                        "label": cluster_label,
                        "desc": description,
                        "n": n_clusters,
                        "cluster_id": result[0]
                    }
                )
            else:
                insert_query = text("""
                    INSERT INTO institution_clusters 
                    (institution_id, cluster_label, cluster_description, cluster_method, n_clusters)
                    VALUES (:inst_id, :label, :desc, :method, :n)
                """)
                conn.execute(
                    insert_query,
                    {
                        "inst_id": cluster["institution_id"],
                        "label": cluster_label,
                        "desc": description,
                        "method": method,
                        "n": n_clusters
                    }
                )
            conn.commit()
    
    logger.info("Clusters saved to database")


def compute_sensitivity_analysis(year: int = DEFAULT_YEAR) -> List[Dict]:
    """
    Compute sensitivity/volatility analysis to measure how much
    institutions move under different methodology assumptions.
    """
    logger.info("Computing sensitivity analysis...")
    
    engine = create_db_engine()
    
    # Get rankings for all methodologies
    query = text("""
        SELECT 
            r.institution_id,
            i.institution_name,
            i.country,
            r.methodology_name,
            r.rank_position
        FROM ranking_results r
        JOIN institutions i ON r.institution_id = i.institution_id
        WHERE r.year = :year
          AND r.subject_id IS NULL
    """)
    
    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params={"year": year})
    
    if df.empty:
        logger.warning("No data found for sensitivity analysis")
        return []
    
    # Compute volatility metrics for each institution
    sensitivity_results = []
    
    for institution_id in df["institution_id"].unique():
        inst_df = df[df["institution_id"] == institution_id]
        
        ranks = inst_df["rank_position"].values
        avg_rank = float(np.mean(ranks))
        min_rank = int(np.min(ranks))
        max_rank = int(np.max(ranks))
        rank_range = max_rank - min_rank
        
        # Volatility score: coefficient of variation
        if avg_rank > 0:
            volatility_score = float(np.std(ranks) / avg_rank) if avg_rank > 0 else 0.0
        else:
            volatility_score = 0.0
        
        institution_name = inst_df["institution_name"].iloc[0]
        country = inst_df["country"].iloc[0]
        
        sensitivity_results.append({
            "institution_id": int(institution_id),
            "institution_name": institution_name,
            "country": country,
            "volatility_score": volatility_score,
            "average_rank": avg_rank,
            "rank_range": rank_range,
            "min_rank": min_rank,
            "max_rank": max_rank,
            "methodology_count": len(ranks)
        })
    
    logger.info(f"Computed sensitivity for {len(sensitivity_results)} institutions")
    return sensitivity_results


def save_sensitivity_to_db(sensitivity_results: List[Dict], year: int = DEFAULT_YEAR) -> None:
    """Save sensitivity analysis results to database."""
    logger.info(f"Saving {len(sensitivity_results)} sensitivity results...")
    
    engine = create_db_engine()
    
    with engine.connect() as conn:
        for result in sensitivity_results:
            check_query = text("""
                SELECT sensitivity_id FROM sensitivity_results 
                WHERE institution_id = :inst_id AND year = :year AND subject_id IS NULL
            """)
            db_result = conn.execute(
                check_query,
                {"inst_id": result["institution_id"], "year": year}
            ).fetchone()
            
            if db_result:
                update_query = text("""
                    UPDATE sensitivity_results 
                    SET volatility_score = :vol, average_rank = :avg, rank_range = :range,
                        methodology_count = :count, min_rank = :min, max_rank = :max
                    WHERE sensitivity_id = :sens_id
                """)
                conn.execute(
                    update_query,
                    {
                        "vol": result["volatility_score"],
                        "avg": result["average_rank"],
                        "range": result["rank_range"],
                        "count": result["methodology_count"],
                        "min": result["min_rank"],
                        "max": result["max_rank"],
                        "sens_id": db_result[0]
                    }
                )
            else:
                insert_query = text("""
                    INSERT INTO sensitivity_results 
                    (institution_id, year, volatility_score, average_rank, rank_range,
                     methodology_count, min_rank, max_rank)
                    VALUES (:inst_id, :year, :vol, :avg, :range, :count, :min, :max)
                """)
                conn.execute(
                    insert_query,
                    {
                        "inst_id": result["institution_id"],
                        "year": year,
                        "vol": result["volatility_score"],
                        "avg": result["average_rank"],
                        "range": result["rank_range"],
                        "count": result["methodology_count"],
                        "min": result["min_rank"],
                        "max": result["max_rank"]
                    }
                )
            conn.commit()
    
    logger.info("Sensitivity results saved to database")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Compute feature importance
    importance = compute_feature_importance()
    logger.info(f"Feature importance: {importance}")
    
    # Compute clusters
    clusters = compute_institution_clusters(n_clusters=4)
    if clusters:
        save_clusters_to_db(clusters)
    
    # Compute sensitivity
    sensitivity = compute_sensitivity_analysis()
    if sensitivity:
        save_sensitivity_to_db(sensitivity)
