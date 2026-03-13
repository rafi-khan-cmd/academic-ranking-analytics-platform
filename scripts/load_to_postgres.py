"""
Database loading module.
Loads processed data into PostgreSQL tables.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from scripts.database import create_db_engine, execute_sql_file
from scripts.config import PROJECT_ROOT, PROCESSED_DATA_DIR, NORMALIZATION_METHOD

logger = logging.getLogger(__name__)


def to_python_scalar(value: Any) -> Any:
    """
    Convert NumPy/pandas scalar types to native Python primitives for database insertion.
    
    PostgreSQL doesn't understand NumPy types like np.float64, np.int64, etc.
    This function ensures all values are plain Python types.
    
    Args:
        value: Value that may be a NumPy scalar, pandas NA, or regular Python type
    
    Returns:
        Native Python type (int, float, bool, None, or original value)
    """
    if value is None:
        return None
    
    # Handle NumPy scalars
    try:
        import numpy as np
        if isinstance(value, (np.integer, np.int_, np.intc, np.intp, np.int8,
                             np.int16, np.int32, np.int64, np.uint8, np.uint16,
                             np.uint32, np.uint64)):
            return int(value.item())
        elif isinstance(value, (np.floating, np.float_, np.float16, np.float32, np.float64)):
            # Check for NaN before converting
            if np.isnan(value):
                return None
            return float(value.item())
        elif isinstance(value, (np.bool_, np.bool8)):
            return bool(value.item())
    except (ImportError, AttributeError):
        # NumPy not available, skip conversion
        pass
    
    # Handle pandas NA/NaN
    try:
        if pd.isna(value):
            return None
    except (ImportError, TypeError):
        # pandas not available or value not compatible with isna
        pass
    
    # Handle float('nan') and similar
    try:
        import math
        if isinstance(value, float) and math.isnan(value):
            return None
    except (TypeError, ValueError):
        pass
    
    # Handle pandas Timestamp objects
    try:
        if isinstance(value, pd.Timestamp):
            return value.to_pydatetime()
    except (ImportError, AttributeError):
        pass
    
    # Return as-is if already a Python primitive
    return value


def sanitize_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively sanitize all values in a record dictionary to ensure only Python primitives.
    
    This function ensures that NumPy scalars, pandas types, and other non-Python types
    are converted to plain Python types before database insertion.
    
    Args:
        record: Dictionary that may contain NumPy/pandas types
    
    Returns:
        Dictionary with all values converted to Python primitives
    """
    if not isinstance(record, dict):
        # If not a dict, just sanitize the value directly
        return to_python_scalar(record)
    
    sanitized = {}
    for key, value in record.items():
        if isinstance(value, dict):
            # Recursively sanitize nested dictionaries
            sanitized[key] = sanitize_record(value)
        elif isinstance(value, (list, tuple)):
            # Sanitize list/tuple elements
            sanitized[key] = [to_python_scalar(item) for item in value]
        else:
            # Sanitize scalar values
            sanitized[key] = to_python_scalar(value)
    return sanitized


def initialize_database() -> None:
    """Initialize database schema."""
    logger.info("Initializing database schema...")
    engine = create_db_engine()
    
    schema_file = PROJECT_ROOT / "sql" / "schema.sql"
    views_file = PROJECT_ROOT / "sql" / "views.sql"
    
    execute_sql_file(engine, schema_file)
    execute_sql_file(engine, views_file)
    
    logger.info("Database schema initialized")


def load_institutions(resolved_institutions: List[Dict]) -> Dict[str, int]:
    """
    Load institutions into database using bulk upsert and return mapping of canonical_name to institution_id.
    
    Uses INSERT ... ON CONFLICT for efficient bulk loading with batching and retry logic.
    """
    logger.info(f"Loading {len(resolved_institutions)} institutions in bulk...")
    
    if not resolved_institutions:
        logger.warning("No institutions to load")
        return {}
    
    engine = create_db_engine()
    chunk_size = 50  # Process 50 institutions per batch
    
    # Prepare institution rows for bulk insert
    institution_rows = []
    for inst in resolved_institutions:
        institution_rows.append({
            "institution_name": inst.get("institution_name", ""),
            "canonical_name": inst.get("canonical_name", ""),
            "ror_id": inst.get("ror_id"),
            "country": inst.get("country"),
            "region": inst.get("region"),
            "institution_type": inst.get("institution_type"),
            "openalex_id": inst.get("openalex_id")
        })
    
    # Bulk upsert in chunks with retry logic
    total_chunks = (len(institution_rows) + chunk_size - 1) // chunk_size
    logger.info(f"Upserting {len(institution_rows)} institutions in {total_chunks} chunks of {chunk_size}")
    
    # Define INSERT columns (must match tuple shape exactly)
    INSERT_COLUMNS = [
        "institution_name",
        "canonical_name", 
        "ror_id",
        "country",
        "region",
        "institution_type",
        "openalex_id",
        "updated_at"
    ]
    NUM_COLUMNS = len(INSERT_COLUMNS)
    
    # Helper function to build institution row tuple
    def build_institution_row(row: Dict[str, Any]) -> tuple:
        """Build a tuple for one institution row matching INSERT_COLUMNS exactly."""
        return (
            row.get("institution_name", ""),
            row.get("canonical_name", ""),
            row.get("ror_id"),
            row.get("country"),
            row.get("region"),
            row.get("institution_type"),
            row.get("openalex_id"),
            datetime.now()  # updated_at - must be included in tuple
        )
    
    # Bulk upsert query (for fallback row-by-row path)
    upsert_query = text("""
        INSERT INTO institutions 
        (institution_name, canonical_name, ror_id, country, region, institution_type, openalex_id, updated_at)
        VALUES (:institution_name, :canonical_name, :ror_id, :country, :region, :institution_type, :openalex_id, CURRENT_TIMESTAMP)
        ON CONFLICT (canonical_name, country) 
        DO UPDATE SET
            institution_name = EXCLUDED.institution_name,
            ror_id = EXCLUDED.ror_id,
            region = EXCLUDED.region,
            institution_type = EXCLUDED.institution_type,
            openalex_id = EXCLUDED.openalex_id,
            updated_at = CURRENT_TIMESTAMP
    """)
    
    for chunk_idx in range(0, len(institution_rows), chunk_size):
        chunk = institution_rows[chunk_idx:chunk_idx + chunk_size]
        chunk_num = (chunk_idx // chunk_size) + 1
        
        max_retries = 2
        retry_count = 0
        success = False
        
        while retry_count <= max_retries and not success:
            try:
                with engine.connect() as conn:
                    # Use psycopg2's execute_values for true bulk insert (one round-trip)
                    # Falls back to row-by-row if psycopg2.extras not available
                    try:
                        from psycopg2.extras import execute_values
                        # Get raw psycopg2 connection from SQLAlchemy Connection
                        # Try multiple ways to access the raw connection
                        raw_conn = None
                        if hasattr(conn, 'connection'):
                            raw_conn = getattr(conn.connection, 'dbapi_connection', None) or getattr(conn.connection, 'connection', None)
                        if not raw_conn and hasattr(conn, 'dbapi_connection'):
                            raw_conn = conn.dbapi_connection
                        
                        if raw_conn:
                            cursor = raw_conn.cursor()
                            
                            # Prepare data tuples using centralized helper
                            data_tuples = [build_institution_row(row) for row in chunk]
                            
                            # Validate tuple shape matches INSERT columns
                            if data_tuples:
                                tuple_len = len(data_tuples[0])
                                if tuple_len != NUM_COLUMNS:
                                    first_inst = chunk[0].get("canonical_name", "unknown") if chunk else "unknown"
                                    raise RuntimeError(
                                        f"Tuple length mismatch: INSERT has {NUM_COLUMNS} columns "
                                        f"but tuple has {tuple_len} values. "
                                        f"First institution: {first_inst}. "
                                        f"Columns: {INSERT_COLUMNS}"
                                    )
                                
                                # Debug logging for first chunk only
                                if chunk_num == 1:
                                    logger.debug(
                                        f"Bulk upsert validation: {NUM_COLUMNS} INSERT columns, "
                                        f"tuple length {tuple_len}, chunk size {chunk_size}"
                                    )
                            
                            # Use execute_values for bulk insert with ON CONFLICT
                            execute_values(
                                cursor,
                                f"""
                                INSERT INTO institutions 
                                ({', '.join(INSERT_COLUMNS)})
                                VALUES %s
                                ON CONFLICT (canonical_name, country) 
                                DO UPDATE SET
                                    institution_name = EXCLUDED.institution_name,
                                    ror_id = EXCLUDED.ror_id,
                                    region = EXCLUDED.region,
                                    institution_type = EXCLUDED.institution_type,
                                    openalex_id = EXCLUDED.openalex_id,
                                    updated_at = EXCLUDED.updated_at
                                """,
                                data_tuples,
                                template=None,
                                page_size=chunk_size
                            )
                            raw_conn.commit()
                            cursor.close()
                        else:
                            raise AttributeError("Could not access raw connection")
                    except (AttributeError, ImportError, TypeError):
                        # Fallback: execute each row within one transaction
                        # psycopg2 will still batch these efficiently
                        for row in chunk:
                            conn.execute(upsert_query, row)
                        conn.commit()
                    
                success = True
                first_inst_name = chunk[0].get("canonical_name", "unknown") if chunk else "unknown"
                logger.info(f"Upserted chunk {chunk_num}/{total_chunks} ({len(chunk)} institutions, first: {first_inst_name[:50]})")
            except (OperationalError, Exception) as e:
                retry_count += 1
                first_inst_name = chunk[0].get("canonical_name", "unknown") if chunk else "unknown"
                
                if retry_count > max_retries:
                    error_msg = f"Failed to upsert chunk {chunk_num}/{total_chunks} after {max_retries} retries. First institution: {first_inst_name}. Error: {e}"
                    logger.error(error_msg)
                    raise RuntimeError(error_msg) from e
                else:
                    logger.warning(f"Chunk {chunk_num}/{total_chunks} failed (attempt {retry_count}/{max_retries}), retrying. First institution: {first_inst_name}. Error: {e}")
                    # Recreate engine for retry (handles connection drops)
                    engine = create_db_engine()
                    # Small delay before retry
                    import time
                    time.sleep(0.5)
    
    # Fetch institution_id mapping in one query
    logger.info("Fetching institution_id mapping...")
    
    # Build lookup sets for efficient query
    canonical_names = set(inst.get("canonical_name") for inst in resolved_institutions if inst.get("canonical_name"))
    countries = set(inst.get("country") for inst in resolved_institutions if inst.get("country"))
    
    name_to_id = {}
    max_retries = 2
    retry_count = 0
    success = False
    
    while retry_count <= max_retries and not success:
        try:
            with engine.connect() as conn:
                # Fetch institutions matching our canonical names and countries
                # This is safe and efficient for 200 institutions
                if canonical_names and countries:
                    fetch_query = text("""
                        SELECT institution_id, canonical_name, country 
                        FROM institutions 
                        WHERE canonical_name = ANY(:canonical_names)
                        AND country = ANY(:countries)
                    """)
                    results = conn.execute(
                        fetch_query,
                        {
                            "canonical_names": list(canonical_names),
                            "countries": list(countries)
                        }
                    ).fetchall()
                else:
                    results = []
                
                # Build lookup dict
                lookup_dict = {}
                for row in results:
                    key = (row[1], row[2])  # (canonical_name, country)
                    lookup_dict[key] = row[0]  # institution_id
                
                # Map resolved institutions to IDs
                for inst in resolved_institutions:
                    key = (inst.get("canonical_name"), inst.get("country"))
                    institution_id = lookup_dict.get(key)
                    if institution_id:
                        name_to_id[inst.get("canonical_name")] = institution_id
                    else:
                        logger.warning(f"Institution not found after upsert: {inst.get('canonical_name')}, {inst.get('country')}")
                
            success = True
        except Exception as e:
            retry_count += 1
            if retry_count > max_retries:
                logger.error(f"Failed to fetch institution mapping after {max_retries} retries: {e}")
                raise
            else:
                logger.warning(f"Fetch mapping failed (attempt {retry_count}/{max_retries}), retrying: {e}")
                engine = create_db_engine()
    
    logger.info(f"Fetched institution_id mapping for {len(name_to_id)} institutions")
    return name_to_id


def load_subjects(subjects: List[Dict]) -> Dict[str, int]:
    """Load subjects into database and return mapping of subject_name to subject_id."""
    logger.info(f"Loading {len(subjects)} subjects...")
    
    engine = create_db_engine()
    name_to_id = {}
    
    with engine.connect() as conn:
        for subject in subjects:
            check_query = text("""
                SELECT subject_id FROM subjects WHERE subject_name = :subject_name
            """)
            result = conn.execute(check_query, {"subject_name": subject["subject_name"]}).fetchone()
            
            if result:
                subject_id = result[0]
            else:
                insert_query = text("""
                    INSERT INTO subjects (subject_name, subject_group)
                    VALUES (:subject_name, :subject_group)
                    RETURNING subject_id
                """)
                result = conn.execute(
                    insert_query,
                    {
                        "subject_name": subject["subject_name"],
                        "subject_group": subject.get("subject_group")
                    }
                )
                subject_id = result.fetchone()[0]
                conn.commit()
            
            name_to_id[subject["subject_name"]] = subject_id
    
    logger.info(f"Loaded {len(name_to_id)} subjects")
    return name_to_id


def load_raw_metrics(indicators: List[Dict], institution_map: Dict[str, int]) -> None:
    """Load raw metrics into database using bulk upsert."""
    logger.info(f"Loading {len(indicators)} raw metric records in bulk...")
    
    if not indicators:
        logger.warning("No indicators to load")
        return
    
    engine = create_db_engine()
    chunk_size = 50
    
    # Prepare metric rows for bulk insert
    metric_rows = []
    for indicator in indicators:
        canonical_name = indicator.get("canonical_name")
        institution_id = institution_map.get(canonical_name)
        
        if not institution_id:
            logger.warning(f"Institution not found: {canonical_name}")
            continue
        
        metric_rows.append({
            "institution_id": institution_id,
            "subject_id": None,  # Subject-level metrics not implemented yet
            "year": indicator.get("year"),
            "publication_count": indicator.get("publication_count", 0),
            "citation_count": indicator.get("citation_count", 0),
            "citations_per_paper": indicator.get("citations_per_paper", 0.0),
            "international_collaboration_rate": indicator.get("international_collaboration_rate", 0.0),
            "quality_proxy": indicator.get("quality_proxy", 0.0),
            "productivity_proxy": indicator.get("productivity_proxy", 0.0),
            "h_index": indicator.get("h_index", 0),
            "top_percentile_citations": indicator.get("top_percentile_citations", 0.0)
        })
    
    if not metric_rows:
        logger.warning("No valid metric rows to load")
        return
    
    # Sanitize all metric values to Python primitives (convert NumPy types)
    logger.debug("Sanitizing raw metric values to Python scalars before DB upsert")
    for idx, row in enumerate(metric_rows):
        sanitized_row = sanitize_record(row)
        metric_rows[idx] = sanitized_row
        
        # Debug logging for first row only
        if idx == 0:
            logger.debug("First raw_metrics row types after sanitization:")
            for key, value in sanitized_row.items():
                logger.debug(f"  {key}: {type(value).__name__} = {value}")
    
    # Bulk upsert in chunks
    total_chunks = (len(metric_rows) + chunk_size - 1) // chunk_size
    logger.info(f"Upserting {len(metric_rows)} raw metric records in {total_chunks} chunks of {chunk_size}")
    
    # NOTE: ON CONFLICT (institution_id, subject_id, year) does NOT work correctly when subject_id = NULL
    # because PostgreSQL treats NULL != NULL in unique constraints. This causes duplicate rows on reruns.
    # Solution: Delete existing rows before inserting to ensure idempotency.
    
    insert_query = text("""
        INSERT INTO raw_metrics 
        (institution_id, subject_id, year, publication_count, citation_count, citations_per_paper,
         international_collaboration_rate, quality_proxy, productivity_proxy, h_index, top_percentile_citations)
        VALUES (:institution_id, :subject_id, :year, :publication_count, :citation_count, :citations_per_paper,
                :international_collaboration_rate, :quality_proxy, :productivity_proxy, :h_index, :top_percentile_citations)
    """)
    
    for chunk_idx in range(0, len(metric_rows), chunk_size):
        chunk = metric_rows[chunk_idx:chunk_idx + chunk_size]
        chunk_num = (chunk_idx // chunk_size) + 1
        
        max_retries = 2
        retry_count = 0
        success = False
        
        while retry_count <= max_retries and not success:
            try:
                with engine.connect() as conn:
                    # Delete existing rows for this chunk to ensure idempotency
                    # Handle NULL subject_id explicitly (PostgreSQL NULL != NULL in unique constraints)
                    deleted_count = 0
                    for row in chunk:
                        institution_id = row["institution_id"]
                        subject_id = row["subject_id"]
                        year = row["year"]
                        
                        if subject_id is None:
                            # Delete rows where subject_id IS NULL
                            delete_query = text("""
                                DELETE FROM raw_metrics 
                                WHERE institution_id = :inst_id 
                                  AND year = :year 
                                  AND subject_id IS NULL
                            """)
                        else:
                            # Delete rows where subject_id = value
                            delete_query = text("""
                                DELETE FROM raw_metrics 
                                WHERE institution_id = :inst_id 
                                  AND year = :year 
                                  AND subject_id = :subj_id
                            """)
                        
                        result = conn.execute(
                            delete_query,
                            {"inst_id": institution_id, "year": year, "subj_id": subject_id}
                        )
                        deleted_count += result.rowcount
                    
                    if deleted_count > 0:
                        logger.debug(f"Deleted {deleted_count} existing raw_metrics rows for chunk {chunk_num} before insert")
                    
                    # Insert fresh rows
                    for row in chunk:
                        conn.execute(insert_query, row)
                    conn.commit()
                success = True
                logger.info(f"Upserted raw metrics chunk {chunk_num}/{total_chunks} ({len(chunk)} records, deleted {deleted_count} existing)")
            except Exception as e:
                retry_count += 1
                if retry_count > max_retries:
                    logger.error(f"Failed to upsert raw metrics chunk {chunk_num}/{total_chunks} after {max_retries} retries: {e}")
                    raise
                else:
                    logger.warning(f"Raw metrics chunk {chunk_num}/{total_chunks} failed (attempt {retry_count}/{max_retries}), retrying: {e}")
                    engine = create_db_engine()
    
    logger.info("Raw metrics loaded")


def load_normalized_metrics(normalized_indicators: List[Dict], institution_map: Dict[str, int]) -> None:
    """Load normalized metrics into database using bulk upsert."""
    logger.info(f"Loading {len(normalized_indicators)} normalized metric records in bulk...")
    
    if not normalized_indicators:
        logger.warning("No normalized metrics to load")
        return
    
    engine = create_db_engine()
    chunk_size = 50
    
    # Prepare metric rows for bulk insert
    metric_rows = []
    for metric in normalized_indicators:
        canonical_name = metric.get("canonical_name")
        institution_id = institution_map.get(canonical_name)
        
        if not institution_id:
            continue
        
        metric_rows.append({
            "institution_id": institution_id,
            "subject_id": None,  # Subject-level metrics not implemented yet
            "year": metric.get("year"),
            "publication_score": metric.get("publication_score", 0.0),
            "citation_score": metric.get("citation_score", 0.0),
            "collaboration_score": metric.get("collaboration_score", 0.0),
            "quality_score": metric.get("quality_score", 0.0),
            "subject_strength_score": metric.get("subject_strength_score", 0.0),
            "productivity_score": metric.get("productivity_score", 0.0),
            "normalization_method": NORMALIZATION_METHOD
        })
    
    if not metric_rows:
        logger.warning("No valid normalized metric rows to load")
        return
    
    # Sanitize all metric values to Python primitives (convert NumPy types)
    logger.debug("Sanitizing normalized metric values to Python scalars before DB upsert")
    for idx, row in enumerate(metric_rows):
        sanitized_row = sanitize_record(row)
        metric_rows[idx] = sanitized_row
        
        # Debug logging for first row only
        if idx == 0:
            logger.debug("First normalized_metrics row types after sanitization:")
            for key, value in sanitized_row.items():
                logger.debug(f"  {key}: {type(value).__name__} = {value}")
    
    # Bulk upsert in chunks
    total_chunks = (len(metric_rows) + chunk_size - 1) // chunk_size
    logger.info(f"Upserting {len(metric_rows)} normalized metric records in {total_chunks} chunks of {chunk_size}")
    
    # NOTE: ON CONFLICT (institution_id, subject_id, year) does NOT work correctly when subject_id = NULL
    # because PostgreSQL treats NULL != NULL in unique constraints. This causes duplicate rows on reruns.
    # Solution: Delete existing rows before inserting to ensure idempotency.
    
    insert_query = text("""
        INSERT INTO normalized_metrics 
        (institution_id, subject_id, year, publication_score, citation_score, collaboration_score,
         quality_score, subject_strength_score, productivity_score, normalization_method)
        VALUES (:institution_id, :subject_id, :year, :publication_score, :citation_score, :collaboration_score,
                :quality_score, :subject_strength_score, :productivity_score, :normalization_method)
    """)
    
    for chunk_idx in range(0, len(metric_rows), chunk_size):
        chunk = metric_rows[chunk_idx:chunk_idx + chunk_size]
        chunk_num = (chunk_idx // chunk_size) + 1
        
        max_retries = 2
        retry_count = 0
        success = False
        
        while retry_count <= max_retries and not success:
            try:
                with engine.connect() as conn:
                    # Delete existing rows for this chunk to ensure idempotency
                    # Handle NULL subject_id explicitly (PostgreSQL NULL != NULL in unique constraints)
                    deleted_count = 0
                    for row in chunk:
                        institution_id = row["institution_id"]
                        subject_id = row["subject_id"]
                        year = row["year"]
                        
                        if subject_id is None:
                            # Delete rows where subject_id IS NULL
                            delete_query = text("""
                                DELETE FROM normalized_metrics 
                                WHERE institution_id = :inst_id 
                                  AND year = :year 
                                  AND subject_id IS NULL
                            """)
                        else:
                            # Delete rows where subject_id = value
                            delete_query = text("""
                                DELETE FROM normalized_metrics 
                                WHERE institution_id = :inst_id 
                                  AND year = :year 
                                  AND subject_id = :subj_id
                            """)
                        
                        result = conn.execute(
                            delete_query,
                            {"inst_id": institution_id, "year": year, "subj_id": subject_id}
                        )
                        deleted_count += result.rowcount
                    
                    if deleted_count > 0:
                        logger.debug(f"Deleted {deleted_count} existing normalized_metrics rows for chunk {chunk_num} before insert")
                    
                    # Insert fresh rows
                    for row in chunk:
                        conn.execute(insert_query, row)
                    conn.commit()
                success = True
                logger.info(f"Upserted normalized metrics chunk {chunk_num}/{total_chunks} ({len(chunk)} records, deleted {deleted_count} existing)")
            except Exception as e:
                retry_count += 1
                if retry_count > max_retries:
                    logger.error(f"Failed to upsert normalized metrics chunk {chunk_num}/{total_chunks} after {max_retries} retries: {e}")
                    raise
                else:
                    logger.warning(f"Normalized metrics chunk {chunk_num}/{total_chunks} failed (attempt {retry_count}/{max_retries}), retrying: {e}")
                    engine = create_db_engine()
    
    logger.info("Normalized metrics loaded")


def load_methodology_weights() -> None:
    """Load methodology weights into database."""
    logger.info("Loading methodology weights...")
    
    from scripts.config import METHODOLOGIES
    
    engine = create_db_engine()
    
    with engine.connect() as conn:
        for method_name, weights in METHODOLOGIES.items():
            check_query = text("""
                SELECT methodology_id FROM methodology_weights WHERE methodology_name = :name
            """)
            result = conn.execute(check_query, {"name": method_name}).fetchone()
            
            if not result:
                insert_query = text("""
                    INSERT INTO methodology_weights 
                    (methodology_name, publication_weight, citation_weight, collaboration_weight,
                     quality_weight, subject_strength_weight, productivity_weight, description)
                    VALUES (:name, :pub, :cite, :collab, :quality, :subject, :prod, :desc)
                """)
                conn.execute(
                    insert_query,
                    {
                        "name": method_name,
                        "pub": weights["publication_weight"],
                        "cite": weights["citation_weight"],
                        "collab": weights["collaboration_weight"],
                        "quality": weights["quality_weight"],
                        "subject": weights["subject_strength_weight"],
                        "prod": weights["productivity_weight"],
                        "desc": weights["description"]
                    }
                )
                conn.commit()
    
    logger.info("Methodology weights loaded")


def load_institution_resolution(resolved_institutions: List[Dict], institution_map: Dict[str, int]) -> None:
    """Load institution resolution records into database using bulk upsert."""
    logger.info(f"Loading {len(resolved_institutions)} institution resolution records in bulk...")
    
    if not resolved_institutions:
        logger.warning("No institution resolution records to load")
        return
    
    engine = create_db_engine()
    chunk_size = 50
    
    # Prepare resolution rows for bulk insert
    resolution_rows = []
    for inst in resolved_institutions:
        openalex_id = inst.get("openalex_id")
        canonical_name = inst.get("canonical_name")
        institution_id = institution_map.get(canonical_name)
        
        if not openalex_id:
            continue
        
        resolution_rows.append({
            "institution_id": institution_id,
            "openalex_id": openalex_id,
            "openalex_name": inst.get("institution_name", ""),
            "ror_id": inst.get("ror_id"),
            "resolved_name": inst.get("canonical_name", ""),
            "canonical_name": canonical_name,
            "match_method": inst.get("match_method", "none"),
            "match_confidence": inst.get("match_confidence", 0.0),
            "country": inst.get("country")
        })
    
    if not resolution_rows:
        logger.warning("No valid resolution rows to load")
        return
    
    # Bulk upsert in chunks
    total_chunks = (len(resolution_rows) + chunk_size - 1) // chunk_size
    logger.info(f"Upserting {len(resolution_rows)} resolution records in {total_chunks} chunks of {chunk_size}")
    
    upsert_query = text("""
        INSERT INTO institution_resolution 
        (institution_id, openalex_id, openalex_name, ror_id, resolved_name, 
         canonical_name, match_method, match_confidence, country, updated_at)
        VALUES (:institution_id, :openalex_id, :openalex_name, :ror_id, :resolved_name,
                :canonical_name, :match_method, :match_confidence, :country, CURRENT_TIMESTAMP)
        ON CONFLICT (openalex_id)
        DO UPDATE SET
            institution_id = EXCLUDED.institution_id,
            openalex_name = EXCLUDED.openalex_name,
            ror_id = EXCLUDED.ror_id,
            resolved_name = EXCLUDED.resolved_name,
            canonical_name = EXCLUDED.canonical_name,
            match_method = EXCLUDED.match_method,
            match_confidence = EXCLUDED.match_confidence,
            country = EXCLUDED.country,
            updated_at = CURRENT_TIMESTAMP
    """)
    
    for chunk_idx in range(0, len(resolution_rows), chunk_size):
        chunk = resolution_rows[chunk_idx:chunk_idx + chunk_size]
        chunk_num = (chunk_idx // chunk_size) + 1
        
        max_retries = 2
        retry_count = 0
        success = False
        
        while retry_count <= max_retries and not success:
            try:
                with engine.connect() as conn:
                    # Execute each row in chunk (batched efficiently by psycopg2)
                    for row in chunk:
                        conn.execute(upsert_query, row)
                    conn.commit()
                success = True
                logger.info(f"Upserted resolution chunk {chunk_num}/{total_chunks} ({len(chunk)} records)")
            except Exception as e:
                retry_count += 1
                if retry_count > max_retries:
                    logger.error(f"Failed to upsert resolution chunk {chunk_num}/{total_chunks} after {max_retries} retries: {e}")
                    raise
                else:
                    logger.warning(f"Resolution chunk {chunk_num}/{total_chunks} failed (attempt {retry_count}/{max_retries}), retrying: {e}")
                    engine = create_db_engine()
    
    logger.info("Institution resolution records loaded")


def load_topics(topics: List[Dict]) -> Dict[str, int]:
    """Load topics into database and return mapping of openalex_topic_id to topic_id."""
    logger.info(f"Loading {len(topics)} topics...")
    
    engine = create_db_engine()
    topic_map = {}
    
    with engine.connect() as conn:
        for topic in topics:
            openalex_id = topic.get("id", "").split("/")[-1] if topic.get("id") else None
            if not openalex_id:
                continue
            
            # Check if topic exists
            check_query = text("""
                SELECT topic_id FROM topics WHERE openalex_topic_id = :openalex_id
            """)
            result = conn.execute(check_query, {"openalex_id": openalex_id}).fetchone()
            
            if result:
                topic_id = result[0]
            else:
                insert_query = text("""
                    INSERT INTO topics 
                    (openalex_topic_id, topic_name, domain, field, subfield, 
                     custom_subject_group, works_count, cited_by_count)
                    VALUES (:openalex_id, :name, :domain, :field, :subfield,
                            :subject_group, :works_count, :cited_by_count)
                    RETURNING topic_id
                """)
                result = conn.execute(
                    insert_query,
                    {
                        "openalex_id": openalex_id,
                        "name": topic.get("display_name", ""),
                        "domain": topic.get("domain", {}).get("display_name") if topic.get("domain") else None,
                        "field": topic.get("field", {}).get("display_name") if topic.get("field") else None,
                        "subfield": topic.get("subfield", {}).get("display_name") if topic.get("subfield") else None,
                        "subject_group": None,  # Would need mapping logic
                        "works_count": topic.get("works_count", 0),
                        "cited_by_count": topic.get("cited_by_count", 0)
                    }
                )
                topic_id = result.fetchone()[0]
                conn.commit()
            
            topic_map[openalex_id] = topic_id
    
    logger.info(f"Loaded {len(topic_map)} topics")
    return topic_map


def load_works(works_data_map: Dict[str, List[Dict]], topic_map: Optional[Dict[str, int]] = None) -> Dict[str, int]:
    """Load works into database and return mapping of openalex_work_id to work_id."""
    if not works_data_map:
        logger.info("No works data to load (works_data_map is empty)")
        return {}
    
    logger.info(f"Loading works from {len(works_data_map)} institutions...")
    
    engine = create_db_engine()
    work_map = {}
    work_topic_relations = []
    institution_work_relations = []
    
    with engine.connect() as conn:
        for inst_id, works_list in works_data_map.items():
            for work in works_list:
                openalex_work_id = work.get("id", "").split("/")[-1] if work.get("id") else None
                if not openalex_work_id:
                    continue
                
                # Check if work exists
                check_query = text("""
                    SELECT work_id FROM works WHERE openalex_work_id = :openalex_id
                """)
                result = conn.execute(check_query, {"openalex_id": openalex_work_id}).fetchone()
                
                if result:
                    work_id = result[0]
                else:
                    # Extract publication date
                    pub_date = None
                    pub_year = work.get("publication_year")
                    if pub_year:
                        try:
                            pub_date = f"{pub_year}-01-01"
                        except:
                            pass
                    
                    insert_query = text("""
                        INSERT INTO works 
                        (openalex_work_id, title, publication_year, publication_date, doi,
                         work_type, cited_by_count, source_name, source_id, language,
                         is_retracted, is_paratext)
                        VALUES (:openalex_id, :title, :year, :date, :doi,
                                :type, :cited_by, :source_name, :source_id, :language,
                                :retracted, :paratext)
                        RETURNING work_id
                    """)
                    result = conn.execute(
                        insert_query,
                        {
                            "openalex_id": openalex_work_id,
                            "title": work.get("title", ""),
                            "year": pub_year,
                            "date": pub_date,
                            "doi": work.get("doi"),
                            "type": work.get("type"),
                            "cited_by": work.get("cited_by_count", 0),
                            "source_name": work.get("primary_location", {}).get("source", {}).get("display_name") if work.get("primary_location") else None,
                            "source_id": work.get("primary_location", {}).get("source", {}).get("id", "").split("/")[-1] if work.get("primary_location") and work.get("primary_location", {}).get("source") else None,
                            "language": work.get("language"),
                            "retracted": work.get("is_retracted", False),
                            "paratext": work.get("is_paratext", False)
                        }
                    )
                    work_id = result.fetchone()[0]
                    conn.commit()
                
                work_map[openalex_work_id] = work_id
                
                # Collect topic relations
                if topic_map:
                    topics = work.get("topics", [])
                    for topic in topics:
                        topic_id_str = topic.get("id", "").split("/")[-1] if topic.get("id") else None
                        if topic_id_str and topic_id_str in topic_map:
                            work_topic_relations.append({
                                "work_id": work_id,
                                "topic_id": topic_map[topic_id_str],
                                "score": topic.get("score")
                            })
                
                # Collect institution-work relations
                authorships = work.get("authorships", [])
                for i, authorship in enumerate(authorships):
                    institutions = authorship.get("institutions", [])
                    for inst in institutions:
                        inst_id_str = inst.get("id", "").split("/")[-1] if inst.get("id") else None
                        if inst_id_str == inst_id:  # Match the current institution
                            institution_work_relations.append({
                                "institution_id": None,  # Will be resolved later
                                "work_id": work_id,
                                "is_primary": i == 0,  # First authorship is primary
                                "author_position": i + 1
                            })
        
        # Bulk insert work-topic relations
        if work_topic_relations:
            logger.info(f"Loading {len(work_topic_relations)} work-topic relations...")
            for rel in work_topic_relations:
                check_query = text("""
                    SELECT work_topic_id FROM work_topics 
                    WHERE work_id = :work_id AND topic_id = :topic_id
                """)
                if not conn.execute(check_query, rel).fetchone():
                    insert_query = text("""
                        INSERT INTO work_topics (work_id, topic_id, score)
                        VALUES (:work_id, :topic_id, :score)
                    """)
                    conn.execute(insert_query, rel)
            conn.commit()
    
    logger.info(f"Loaded {len(work_map)} works")
    return work_map


def log_api_ingestion(
    source_name: str,
    entity_type: str,
    status: str,
    records_fetched: int = 0,
    records_processed: int = 0,
    records_failed: int = 0,
    notes: Optional[str] = None,
    config_json: Optional[Dict] = None
) -> int:
    """Log API ingestion run and return log_id."""
    engine = create_db_engine()
    
    with engine.connect() as conn:
        insert_query = text("""
            INSERT INTO api_ingestion_log 
            (source_name, entity_type, started_at, completed_at, status,
             records_fetched, records_processed, records_failed, notes, config_json)
            VALUES (:source, :entity_type, :started, :completed, :status,
                    :fetched, :processed, :failed, :notes, :config)
            RETURNING log_id
        """)
        result = conn.execute(
            insert_query,
            {
                "source": source_name,
                "entity_type": entity_type,
                "started": datetime.now(),
                "completed": datetime.now() if status in ["completed", "failed"] else None,
                "status": status,
                "fetched": records_fetched,
                "processed": records_processed,
                "failed": records_failed,
                "notes": notes,
                "config": json.dumps(config_json) if config_json else None
            }
        )
        log_id = result.fetchone()[0]
        conn.commit()
    
    return log_id


def load_benchmark_rankings(rankings: List[Dict], institution_map: Dict[str, int]) -> None:
    """Load benchmark rankings into database."""
    logger.info(f"Loading {len(rankings)} benchmark ranking records...")
    
    engine = create_db_engine()
    
    with engine.connect() as conn:
        for ranking in rankings:
            canonical_name = ranking.get("canonical_name")
            institution_id = institution_map.get(canonical_name) if canonical_name else None
            
            check_query = text("""
                SELECT benchmark_id FROM benchmark_rankings 
                WHERE benchmark_source = :source AND year = :year 
                  AND institution_name_raw = :name_raw
            """)
            result = conn.execute(
                check_query,
                {
                    "source": ranking.get("benchmark_source"),
                    "year": ranking.get("year"),
                    "name_raw": ranking.get("institution_name_raw")
                }
            ).fetchone()
            
            if not result:
                insert_query = text("""
                    INSERT INTO benchmark_rankings 
                    (benchmark_source, year, institution_name_raw, canonical_name,
                     institution_id, rank, score, metadata_json)
                    VALUES (:source, :year, :name_raw, :canonical_name,
                            :institution_id, :rank, :score, :metadata)
                """)
                conn.execute(
                    insert_query,
                    {
                        "source": ranking.get("benchmark_source"),
                        "year": ranking.get("year"),
                        "name_raw": ranking.get("institution_name_raw"),
                        "canonical_name": canonical_name,
                        "institution_id": institution_id,
                        "rank": ranking.get("rank"),
                        "score": ranking.get("score"),
                        "metadata": json.dumps(ranking.get("metadata", {}))
                    }
                )
                conn.commit()
    
    logger.info("Benchmark rankings loaded")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Initialize database
    initialize_database()
    
    # Load institutions
    from scripts.resolve_entities import load_resolved_entities
    resolved = load_resolved_entities()
    if resolved:
        institution_map = load_institutions(resolved)
        
        # Load raw metrics
        from scripts.build_indicators import load_indicators
        indicators = load_indicators()
        if indicators:
            load_raw_metrics(indicators, institution_map)
        
        # Load normalized metrics
        from scripts.normalize_metrics import load_normalized_metrics as load_normalized_from_file
        normalized = load_normalized_from_file()
        if normalized:
            load_normalized_metrics(normalized, institution_map)
    
    # Load methodology weights
    load_methodology_weights()
    
    logger.info("Database loading complete")
