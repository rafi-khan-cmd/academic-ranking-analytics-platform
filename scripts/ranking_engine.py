"""
Ranking engine module.
Computes weighted rankings based on methodology profiles.
"""

import logging
from typing import List, Dict, Optional
import pandas as pd
from sqlalchemy import text, bindparam

from scripts.database import create_db_engine, get_db_engine_with_retry
from scripts.config import METHODOLOGIES, DEFAULT_YEAR
from sqlalchemy import Engine

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
                                    subject_id: Optional[int] = None,
                                    institution_ids: Optional[List[int]] = None,
                                    engine: Optional[Engine] = None) -> List[Dict]:
    """
    Compute rankings for a specific methodology.
    
    Args:
        methodology_name: Name of the methodology
        year: Year for ranking computation
        subject_id: Optional subject filter (None for overall rankings)
        institution_ids: Optional list of institution_ids to scope rankings to (None for all)
    
    Returns:
        List of ranking dictionaries with institution_id, score, and rank
    """
    scope_info = f" (scoped to {len(institution_ids)} institutions)" if institution_ids else " (all institutions)"
    logger.info(f"Computing rankings for {methodology_name} (year={year}, subject_id={subject_id}){scope_info}...")
    
    if methodology_name not in METHODOLOGIES:
        logger.error(f"Unknown methodology: {methodology_name}")
        return []
    
    weights = METHODOLOGIES[methodology_name]
    
    # Use provided engine or get shared engine
    if engine is None:
        engine = create_db_engine()
    
    # Build query with optional institution_id filtering
    if institution_ids:
        # Use IN clause with bindparam expanding=True for proper list parameter binding
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
            AND nm.institution_id IN :institution_ids
        """).bindparams(bindparam('institution_ids', expanding=True))
        params = {"year": year, "subject_id": subject_id, "institution_ids": institution_ids}
    else:
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
        params = {"year": year, "subject_id": subject_id}
    
    with engine.connect() as conn:
        result = conn.execute(query, params)
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
                        year: int = DEFAULT_YEAR, subject_id: Optional[int] = None,
                        engine: Optional[Engine] = None) -> None:
    """
    Save computed rankings to database.
    
    Args:
        rankings: List of ranking dictionaries
        methodology_name: Name of methodology
        year: Year for rankings
        subject_id: Optional subject ID
        engine: Optional SQLAlchemy engine (if None, creates/reuses shared engine)
    """
    logger.info(f"Saving {len(rankings)} rankings to database...")
    
    # Use provided engine or get shared engine
    if engine is None:
        engine = create_db_engine()
    
    with engine.begin() as conn:  # Use begin() for transaction management
        # Delete existing rankings for this methodology/year/subject combination first
        # This ensures idempotency: rerunning produces the same result without duplicates
        # Use a simpler query that handles NULL correctly
        if subject_id is None:
            delete_query = text("""
                DELETE FROM ranking_results 
                WHERE year = :year 
                  AND methodology_name = :method
                  AND subject_id IS NULL
            """)
            delete_params = {
                "year": year,
                "method": methodology_name
            }
        else:
            delete_query = text("""
                DELETE FROM ranking_results 
                WHERE year = :year 
                  AND methodology_name = :method
                  AND subject_id = :subj_id
            """)
            delete_params = {
                "year": year,
                "method": methodology_name,
                "subj_id": subject_id
            }
        
        result = conn.execute(delete_query, delete_params)
        deleted_count = result.rowcount
        if deleted_count > 0:
            logger.info(
                f"Deleted {deleted_count} existing ranking_results rows for methodology={methodology_name}, "
                f"year={year}, subject_id={subject_id}"
            )
        
        # Insert fresh rankings
        insert_query = text("""
            INSERT INTO ranking_results 
            (institution_id, subject_id, year, methodology_name, overall_score, rank_position)
            VALUES (:inst_id, :subj_id, :year, :method, :score, :rank)
        """)
        
        for ranking in rankings:
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
        # Transaction commits automatically when exiting 'with' block
        
        logger.info(
            f"Upserted {len(rankings)} rankings idempotently for methodology={methodology_name}, "
            f"year={year}, subject_id={subject_id}"
        )
    
    logger.info("Rankings saved to database")


def compute_all_methodology_rankings(year: int = DEFAULT_YEAR, 
                                    subject_id: Optional[int] = None,
                                    institution_ids: Optional[List[int]] = None) -> None:
    """
    Compute rankings for all methodologies using a single shared engine.
    
    Reuses the same database engine across all methodology computations to prevent
    connection exhaustion in Supabase pooler mode.
    """
    scope_info = f" (scoped to {len(institution_ids)} institutions)" if institution_ids else " (all institutions)"
    logger.info(f"Computing rankings for all methodologies (year={year}){scope_info}...")
    
    # Get shared engine once and reuse across all methodologies
    try:
        engine = get_db_engine_with_retry()
        
        for methodology_name in METHODOLOGIES.keys():
            rankings = compute_rankings_for_methodology(
                methodology_name, year, subject_id, 
                institution_ids=institution_ids,
                engine=engine  # Reuse same engine
            )
            save_rankings_to_db(
                rankings, methodology_name, year, subject_id,
                engine=engine  # Reuse same engine
            )
        
        logger.info("All methodology rankings computed")
    except Exception as e:
        logger.error(f"Error computing rankings: {e}")
        raise


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    compute_all_methodology_rankings()
