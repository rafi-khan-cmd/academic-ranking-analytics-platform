"""
Ranking engine module.
Computes weighted rankings based on methodology profiles.
"""

import logging
from typing import List, Dict, Optional
import pandas as pd
from sqlalchemy import text

from scripts.database import create_db_engine
from scripts.config import METHODOLOGIES, DEFAULT_YEAR

logger = logging.getLogger(__name__)


def compute_weighted_score(normalized_metrics: Dict, weights: Dict) -> float:
    """
    Compute weighted overall score from normalized metrics.
    
    Args:
        normalized_metrics: Dictionary with normalized indicator scores
        weights: Dictionary with weight values for each indicator
    
    Returns:
        Overall weighted score
    """
    score = (
        normalized_metrics.get("publication_score", 0.0) * weights.get("publication_weight", 0.0) +
        normalized_metrics.get("citation_score", 0.0) * weights.get("citation_weight", 0.0) +
        normalized_metrics.get("collaboration_score", 0.0) * weights.get("collaboration_weight", 0.0) +
        normalized_metrics.get("quality_score", 0.0) * weights.get("quality_weight", 0.0) +
        normalized_metrics.get("subject_strength_score", 0.0) * weights.get("subject_strength_weight", 0.0) +
        normalized_metrics.get("productivity_score", 0.0) * weights.get("productivity_weight", 0.0)
    )
    
    return score


def compute_rankings_for_methodology(methodology_name: str, year: int = DEFAULT_YEAR,
                                    subject_id: Optional[int] = None) -> List[Dict]:
    """
    Compute rankings for a specific methodology.
    
    Args:
        methodology_name: Name of the methodology
        year: Year for ranking computation
        subject_id: Optional subject filter (None for overall rankings)
    
    Returns:
        List of ranking dictionaries with institution_id, score, and rank
    """
    logger.info(f"Computing rankings for {methodology_name} (year={year}, subject_id={subject_id})...")
    
    if methodology_name not in METHODOLOGIES:
        logger.error(f"Unknown methodology: {methodology_name}")
        return []
    
    weights = METHODOLOGIES[methodology_name]
    engine = create_db_engine()
    
    # Fetch normalized metrics
    query = text("""
        SELECT 
            nm.institution_id,
            nm.publication_score,
            nm.citation_score,
            nm.collaboration_score,
            nm.quality_score,
            nm.subject_strength_score,
            nm.productivity_score
        FROM normalized_metrics nm
        WHERE nm.year = :year
        AND (nm.subject_id = :subject_id OR (:subject_id IS NULL AND nm.subject_id IS NULL))
    """)
    
    with engine.connect() as conn:
        result = conn.execute(query, {"year": year, "subject_id": subject_id})
        rows = result.fetchall()
    
    # Compute scores
    rankings = []
    for row in rows:
        metrics = {
            "institution_id": row[0],
            "publication_score": float(row[1]) if row[1] else 0.0,
            "citation_score": float(row[2]) if row[2] else 0.0,
            "collaboration_score": float(row[3]) if row[3] else 0.0,
            "quality_score": float(row[4]) if row[4] else 0.0,
            "subject_strength_score": float(row[5]) if row[5] else 0.0,
            "productivity_score": float(row[6]) if row[6] else 0.0
        }
        
        overall_score = compute_weighted_score(metrics, weights)
        
        rankings.append({
            "institution_id": metrics["institution_id"],
            "overall_score": overall_score,
            "metrics": metrics
        })
    
    # Sort by score descending and assign ranks
    rankings.sort(key=lambda x: x["overall_score"], reverse=True)
    
    for rank, ranking in enumerate(rankings, start=1):
        ranking["rank_position"] = rank
    
    logger.info(f"Computed {len(rankings)} rankings")
    return rankings


def save_rankings_to_db(rankings: List[Dict], methodology_name: str, 
                        year: int = DEFAULT_YEAR, subject_id: Optional[int] = None) -> None:
    """Save computed rankings to database."""
    logger.info(f"Saving {len(rankings)} rankings to database...")
    
    engine = create_db_engine()
    
    with engine.connect() as conn:
        for ranking in rankings:
            # Check if ranking already exists
            check_query = text("""
                SELECT ranking_id FROM ranking_results 
                WHERE institution_id = :inst_id 
                  AND year = :year 
                  AND methodology_name = :method
                  AND (subject_id = :subj_id OR (:subj_id IS NULL AND subject_id IS NULL))
            """)
            result = conn.execute(
                check_query,
                {
                    "inst_id": ranking["institution_id"],
                    "year": year,
                    "method": methodology_name,
                    "subj_id": subject_id
                }
            ).fetchone()
            
            if result:
                # Update existing ranking
                update_query = text("""
                    UPDATE ranking_results 
                    SET overall_score = :score, rank_position = :rank
                    WHERE ranking_id = :ranking_id
                """)
                conn.execute(
                    update_query,
                    {
                        "score": ranking["overall_score"],
                        "rank": ranking["rank_position"],
                        "ranking_id": result[0]
                    }
                )
            else:
                # Insert new ranking
                insert_query = text("""
                    INSERT INTO ranking_results 
                    (institution_id, subject_id, year, methodology_name, overall_score, rank_position)
                    VALUES (:inst_id, :subj_id, :year, :method, :score, :rank)
                """)
                conn.execute(
                    insert_query,
                    {
                        "inst_id": ranking["institution_id"],
                        "subj_id": subject_id,
                        "year": year,
                        "method": methodology_name,
                        "score": ranking["overall_score"],
                        "rank": ranking["rank_position"]
                    }
                )
            conn.commit()
    
    logger.info("Rankings saved to database")


def compute_all_methodology_rankings(year: int = DEFAULT_YEAR, 
                                    subject_id: Optional[int] = None) -> None:
    """Compute rankings for all methodologies."""
    logger.info(f"Computing rankings for all methodologies (year={year})...")
    
    for methodology_name in METHODOLOGIES.keys():
        rankings = compute_rankings_for_methodology(methodology_name, year, subject_id)
        save_rankings_to_db(rankings, methodology_name, year, subject_id)
    
    logger.info("All methodology rankings computed")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    compute_all_methodology_rankings()
