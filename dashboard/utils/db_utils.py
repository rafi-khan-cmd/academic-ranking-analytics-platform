"""
Database utility functions for Streamlit dashboard.
"""

import pandas as pd
from sqlalchemy import text
import logging
from scripts.database import create_db_engine, test_connection
from scripts.config import DEFAULT_YEAR

logger = logging.getLogger(__name__)


def get_db_connection():
    """Get database connection for dashboard."""
    try:
        engine = create_db_engine()
        return engine.connect()
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise


def check_database_available():
    """Check if database is available and has data."""
    from scripts.database import test_connection
    from scripts.config import DB_CONFIG
    
    # Log current config (without password) for debugging
    logger.info(f"Attempting connection to: {DB_CONFIG.get('user', 'N/A')}@{DB_CONFIG.get('host', 'N/A')}:{DB_CONFIG.get('port', 'N/A')}/{DB_CONFIG.get('database', 'N/A')}")
    
    # Test connection with fallback ports
    connected, conn_message = test_connection()
    if not connected:
        # Provide specific guidance based on error
        error_lower = conn_message.lower()
        if "connection refused" in error_lower or "could not connect" in error_lower:
            return False, (
                f"⚠️ Connection refused.\n\n"
                f"**Current config:**\n"
                f"- Host: {DB_CONFIG.get('host', 'NOT SET')}\n"
                f"- Port: {DB_CONFIG.get('port', 'NOT SET')}\n"
                f"- User: {DB_CONFIG.get('user', 'NOT SET')}\n"
                f"- Database: {DB_CONFIG.get('database', 'NOT SET')}\n\n"
                f"**Fix:** Use Session Pooler connection string from Supabase:\n"
                f"1. Supabase → Settings → Database → Connection string\n"
                f"2. Click 'Session Pooler' tab\n"
                f"3. Copy the connection string\n"
                f"4. Update Streamlit secrets with those exact values"
            )
        elif "authentication" in error_lower or "password" in error_lower:
            return False, (
                f"⚠️ Authentication failed.\n\n"
                f"**Check:**\n"
                f"- Password in Streamlit secrets matches Supabase\n"
                f"- User includes project ID: `postgres.peawexmwwmkqszcdqwjv`\n"
                f"- No extra spaces or quotes in secrets"
            )
        return False, f"⚠️ {conn_message}"
    
    # Query for data
    try:
        engine = create_db_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM institutions"))
            count = result.fetchone()[0]
            if count == 0:
                return False, "Database is empty. Run: python scripts/create_sample_data.py && python scripts/load_to_postgres.py"
            return True, f"✅ Database connected with {count} institutions."
    except Exception as query_error:
        error_msg = str(query_error).lower()
        if "does not exist" in error_msg or "relation" in error_msg:
            return False, "Schema not created. Run sql/schema.sql in Supabase SQL Editor."
        return False, f"Query error: {str(query_error)[:100]}"


def fetch_top_rankings(methodology: str = "Balanced Model", limit: int = 20, 
                      year: int = DEFAULT_YEAR, country: str = None) -> pd.DataFrame:
    """Fetch top rankings from database."""
    try:
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
        try:
            with engine.connect() as conn:
                df = pd.read_sql(
                    query, 
                    conn, 
                    params={"method": methodology, "year": year, "country": country, "limit": limit}
                )
            return df
        finally:
            engine.dispose()
    except Exception as e:
        logger.error(f"Error fetching rankings: {e}")
        return pd.DataFrame()  # Return empty DataFrame on error


def fetch_institution_details(institution_name: str, year: int = DEFAULT_YEAR) -> pd.DataFrame:
    """Fetch detailed information for a specific institution."""
    try:
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
    except Exception as e:
        logger.error(f"Error fetching institution details: {e}")
        return pd.DataFrame()


def fetch_institution_rankings(institution_id: int, year: int = DEFAULT_YEAR) -> pd.DataFrame:
    """Fetch rankings for an institution across all methodologies."""
    try:
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
    except Exception as e:
        logger.error(f"Error fetching institution rankings: {e}")
        return pd.DataFrame()


def fetch_country_summary(methodology: str = "Balanced Model", year: int = DEFAULT_YEAR) -> pd.DataFrame:
    """Fetch country-level performance summary."""
    try:
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
    except Exception as e:
        logger.error(f"Error fetching country summary: {e}")
        return pd.DataFrame()


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
    try:
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
    except Exception as e:
        logger.error(f"Error fetching institutions: {e}")
        return pd.DataFrame()


def fetch_subjects() -> pd.DataFrame:
    """Fetch list of all subjects."""
    try:
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
    except Exception as e:
        logger.error(f"Error fetching subjects: {e}")
        return pd.DataFrame()
