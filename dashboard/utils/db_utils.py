"""
Database utility functions for Streamlit dashboard.
"""

import pandas as pd
from sqlalchemy import text
from scripts.database import create_db_engine
from scripts.config import DEFAULT_YEAR


def get_db_connection():
    """Get database connection for dashboard."""
    engine = create_db_engine()
    return engine.connect()


def fetch_top_rankings(methodology: str = "Balanced Model", limit: int = 20, 
                      year: int = DEFAULT_YEAR, country: str = None) -> pd.DataFrame:
    """Fetch top rankings from database."""
    query = text("""
        SELECT 
            r.rank_position,
            i.institution_name,
            i.country,
            r.overall_score,
            nm.publication_score,
            nm.citation_score,
            nm.collaboration_score,
            nm.quality_score
        FROM ranking_results r
        JOIN institutions i ON r.institution_id = i.institution_id
        LEFT JOIN normalized_metrics nm ON 
            r.institution_id = nm.institution_id 
            AND r.year = nm.year
            AND nm.subject_id IS NULL
        WHERE r.methodology_name = :method
          AND r.year = :year
          AND r.subject_id IS NULL
          AND (:country IS NULL OR i.country = :country)
        ORDER BY r.rank_position
        LIMIT :limit
    """)
    
    engine = create_db_engine()
    with engine.connect() as conn:
        df = pd.read_sql(
            query, 
            conn, 
            params={"method": methodology, "year": year, "country": country, "limit": limit}
        )
    return df


def fetch_institution_details(institution_name: str, year: int = DEFAULT_YEAR) -> pd.DataFrame:
    """Fetch detailed information for a specific institution."""
    query = text("""
        SELECT 
            i.institution_id,
            i.institution_name,
            i.canonical_name,
            i.country,
            i.region,
            nm.publication_score,
            nm.citation_score,
            nm.collaboration_score,
            nm.quality_score,
            nm.subject_strength_score,
            nm.productivity_score,
            rm.publication_count,
            rm.citation_count,
            rm.citations_per_paper,
            rm.international_collaboration_rate,
            rm.quality_proxy,
            rm.productivity_proxy
        FROM institutions i
        LEFT JOIN normalized_metrics nm ON 
            i.institution_id = nm.institution_id 
            AND nm.year = :year
            AND nm.subject_id IS NULL
        LEFT JOIN raw_metrics rm ON 
            i.institution_id = rm.institution_id 
            AND rm.year = :year
            AND rm.subject_id IS NULL
        WHERE i.canonical_name = :name OR i.institution_name = :name
        LIMIT 1
    """)
    
    engine = create_db_engine()
    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params={"name": institution_name, "year": year})
    return df


def fetch_institution_rankings(institution_id: int, year: int = DEFAULT_YEAR) -> pd.DataFrame:
    """Fetch rankings for an institution across all methodologies."""
    query = text("""
        SELECT 
            r.methodology_name,
            r.overall_score,
            r.rank_position
        FROM ranking_results r
        WHERE r.institution_id = :inst_id
          AND r.year = :year
          AND r.subject_id IS NULL
        ORDER BY r.rank_position
    """)
    
    engine = create_db_engine()
    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params={"inst_id": institution_id, "year": year})
    return df


def fetch_country_summary(methodology: str = "Balanced Model", year: int = DEFAULT_YEAR) -> pd.DataFrame:
    """Fetch country-level performance summary."""
    query = text("""
        SELECT 
            i.country,
            COUNT(DISTINCT i.institution_id) as institution_count,
            AVG(r.overall_score) as avg_score,
            MIN(r.rank_position) as best_rank,
            MAX(r.rank_position) as worst_rank
        FROM ranking_results r
        JOIN institutions i ON r.institution_id = i.institution_id
        WHERE r.methodology_name = :method
          AND r.year = :year
          AND r.subject_id IS NULL
        GROUP BY i.country
        HAVING COUNT(DISTINCT i.institution_id) >= 1
        ORDER BY avg_score DESC
    """)
    
    engine = create_db_engine()
    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params={"method": methodology, "year": year})
    return df


def fetch_sensitivity_data(year: int = DEFAULT_YEAR, limit: int = 20) -> pd.DataFrame:
    """Fetch sensitivity/volatility analysis data."""
    query = text("""
        SELECT 
            i.institution_name,
            i.country,
            sr.volatility_score,
            sr.average_rank,
            sr.rank_range,
            sr.min_rank,
            sr.max_rank
        FROM sensitivity_results sr
        JOIN institutions i ON sr.institution_id = i.institution_id
        WHERE sr.year = :year
          AND sr.subject_id IS NULL
        ORDER BY sr.volatility_score DESC
        LIMIT :limit
    """)
    
    engine = create_db_engine()
    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params={"year": year, "limit": limit})
    return df


def fetch_cluster_data() -> pd.DataFrame:
    """Fetch institution cluster assignments."""
    query = text("""
        SELECT 
            i.institution_name,
            i.country,
            ic.cluster_label,
            ic.cluster_description
        FROM institution_clusters ic
        JOIN institutions i ON ic.institution_id = i.institution_id
        ORDER BY ic.cluster_label, i.institution_name
    """)
    
    engine = create_db_engine()
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    return df


def fetch_all_institutions() -> pd.DataFrame:
    """Fetch list of all institutions for dropdowns."""
    query = text("""
        SELECT DISTINCT
            i.institution_id,
            i.institution_name,
            i.canonical_name,
            i.country
        FROM institutions i
        ORDER BY i.institution_name
    """)
    
    engine = create_db_engine()
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    return df


def fetch_subjects() -> pd.DataFrame:
    """Fetch list of all subjects."""
    query = text("""
        SELECT 
            subject_id,
            subject_name,
            subject_group
        FROM subjects
        ORDER BY subject_name
    """)
    
    engine = create_db_engine()
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    return df
