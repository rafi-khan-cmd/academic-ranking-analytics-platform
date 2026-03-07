"""
Ranking simulator module for dynamic methodology exploration.
Supports live recalculation with custom weights.
"""

import logging
from typing import Dict, List, Optional
import pandas as pd
from sqlalchemy import text

from scripts.database import create_db_engine
from scripts.ranking_engine import compute_weighted_score

logger = logging.getLogger(__name__)


def simulate_rankings(custom_weights: Dict[str, float], year: int = 2023,
                     subject_id: Optional[int] = None, 
                     country_filter: Optional[str] = None) -> List[Dict]:
    """
    Simulate rankings with custom methodology weights.
    
    Args:
        custom_weights: Dictionary with weight values for indicators
        year: Year for ranking computation
        subject_id: Optional subject filter
        country_filter: Optional country filter
    
    Returns:
        List of ranking dictionaries
    """
    logger.info("Simulating rankings with custom weights...")
    
    engine = create_db_engine()
    
    # Build query with optional filters
    query_str = """
        SELECT 
            nm.institution_id,
            i.institution_name,
            i.canonical_name,
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
        AND (nm.subject_id = :subject_id OR (:subject_id IS NULL AND nm.subject_id IS NULL))
    """
    
    params = {"year": year, "subject_id": subject_id}
    
    if country_filter:
        query_str += " AND i.country = :country"
        params["country"] = country_filter
    
    query = text(query_str)
    
    with engine.connect() as conn:
        result = conn.execute(query, params)
        rows = result.fetchall()
    
    # Compute scores and rankings
    rankings = []
    for row in rows:
        metrics = {
            "institution_id": row[0],
            "publication_score": float(row[4]) if row[4] else 0.0,
            "citation_score": float(row[5]) if row[5] else 0.0,
            "collaboration_score": float(row[6]) if row[6] else 0.0,
            "quality_score": float(row[7]) if row[7] else 0.0,
            "subject_strength_score": float(row[8]) if row[8] else 0.0,
            "productivity_score": float(row[9]) if row[9] else 0.0
        }
        
        overall_score = compute_weighted_score(metrics, custom_weights)
        
        rankings.append({
            "institution_id": row[0],
            "institution_name": row[1],
            "canonical_name": row[2],
            "country": row[3],
            "overall_score": overall_score,
            "metrics": metrics
        })
    
    # Sort and assign ranks
    rankings.sort(key=lambda x: x["overall_score"], reverse=True)
    
    for rank, ranking in enumerate(rankings, start=1):
        ranking["rank_position"] = rank
    
    logger.info(f"Simulated {len(rankings)} rankings")
    return rankings


def compare_rankings(baseline_rankings: List[Dict], 
                    simulated_rankings: List[Dict]) -> List[Dict]:
    """
    Compare baseline and simulated rankings to show movement.
    
    Args:
        baseline_rankings: Original rankings
        simulated_rankings: New rankings with custom weights
    
    Returns:
        List of comparison dictionaries with rank changes
    """
    # Create lookup dictionaries
    baseline_lookup = {
        r["institution_id"]: r["rank_position"] 
        for r in baseline_rankings
    }
    
    comparisons = []
    for sim_rank in simulated_rankings:
        inst_id = sim_rank["institution_id"]
        new_rank = sim_rank["rank_position"]
        old_rank = baseline_lookup.get(inst_id)
        
        if old_rank:
            rank_change = old_rank - new_rank  # Positive = moved up
            comparisons.append({
                "institution_id": inst_id,
                "institution_name": sim_rank.get("institution_name"),
                "country": sim_rank.get("country"),
                "old_rank": old_rank,
                "new_rank": new_rank,
                "rank_change": rank_change,
                "old_score": baseline_rankings[old_rank - 1].get("overall_score", 0.0),
                "new_score": sim_rank["overall_score"]
            })
    
    # Sort by absolute rank change
    comparisons.sort(key=lambda x: abs(x["rank_change"]), reverse=True)
    
    return comparisons


def get_baseline_rankings(methodology_name: str, year: int = 2023,
                         subject_id: Optional[int] = None) -> List[Dict]:
    """Get baseline rankings from database for a methodology."""
    engine = create_db_engine()
    
    query = text("""
        SELECT 
            r.institution_id,
            i.institution_name,
            i.canonical_name,
            i.country,
            r.overall_score,
            r.rank_position
        FROM ranking_results r
        JOIN institutions i ON r.institution_id = i.institution_id
        WHERE r.methodology_name = :method
          AND r.year = :year
          AND (r.subject_id = :subject_id OR (:subject_id IS NULL AND r.subject_id IS NULL))
        ORDER BY r.rank_position
    """)
    
    with engine.connect() as conn:
        result = conn.execute(
            query,
            {"method": methodology_name, "year": year, "subject_id": subject_id}
        )
        rows = result.fetchall()
    
    rankings = []
    for row in rows:
        rankings.append({
            "institution_id": row[0],
            "institution_name": row[1],
            "canonical_name": row[2],
            "country": row[3],
            "overall_score": float(row[4]) if row[4] else 0.0,
            "rank_position": int(row[5]) if row[5] else 0
        })
    
    return rankings
