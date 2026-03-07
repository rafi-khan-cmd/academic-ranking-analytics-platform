"""
Database loading module.
Loads processed data into PostgreSQL tables.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd
from sqlalchemy import text

from scripts.database import create_db_engine, execute_sql_file
from scripts.config import PROJECT_ROOT, PROCESSED_DATA_DIR, NORMALIZATION_METHOD

logger = logging.getLogger(__name__)


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
    Load institutions into database and return mapping of canonical_name to institution_id.
    """
    logger.info(f"Loading {len(resolved_institutions)} institutions...")
    
    engine = create_db_engine()
    name_to_id = {}
    
    with engine.connect() as conn:
        for inst in resolved_institutions:
            # Check if institution already exists
            check_query = text("""
                SELECT institution_id FROM institutions 
                WHERE canonical_name = :canonical_name AND country = :country
            """)
            result = conn.execute(
                check_query,
                {
                    "canonical_name": inst.get("canonical_name"),
                    "country": inst.get("country")
                }
            ).fetchone()
            
            if result:
                institution_id = result[0]
            else:
                # Insert new institution
                insert_query = text("""
                    INSERT INTO institutions 
                    (institution_name, canonical_name, ror_id, country, region, institution_type, openalex_id)
                    VALUES (:institution_name, :canonical_name, :ror_id, :country, :region, :institution_type, :openalex_id)
                    RETURNING institution_id
                """)
                result = conn.execute(
                    insert_query,
                    {
                        "institution_name": inst.get("institution_name"),
                        "canonical_name": inst.get("canonical_name"),
                        "ror_id": inst.get("ror_id"),
                        "country": inst.get("country"),
                        "region": inst.get("region"),
                        "institution_type": inst.get("institution_type"),
                        "openalex_id": inst.get("openalex_id")
                    }
                )
                institution_id = result.fetchone()[0]
                conn.commit()
            
            name_to_id[inst.get("canonical_name")] = institution_id
    
    logger.info(f"Loaded {len(name_to_id)} institutions")
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
    """Load raw metrics into database."""
    logger.info(f"Loading {len(indicators)} raw metric records...")
    
    engine = create_db_engine()
    
    with engine.connect() as conn:
        for indicator in indicators:
            canonical_name = indicator.get("canonical_name")
            institution_id = institution_map.get(canonical_name)
            
            if not institution_id:
                logger.warning(f"Institution not found: {canonical_name}")
                continue
            
            # Check if record exists
            check_query = text("""
                SELECT metric_id FROM raw_metrics 
                WHERE institution_id = :institution_id AND year = :year
            """)
            result = conn.execute(
                check_query,
                {
                    "institution_id": institution_id,
                    "year": indicator.get("year")
                }
            ).fetchone()
            
            if not result:
                insert_query = text("""
                    INSERT INTO raw_metrics 
                    (institution_id, year, publication_count, citation_count, citations_per_paper,
                     international_collaboration_rate, quality_proxy, productivity_proxy, h_index, top_percentile_citations)
                    VALUES (:institution_id, :year, :publication_count, :citation_count, :citations_per_paper,
                            :international_collaboration_rate, :quality_proxy, :productivity_proxy, :h_index, :top_percentile_citations)
                """)
                conn.execute(
                    insert_query,
                    {
                        "institution_id": institution_id,
                        "year": indicator.get("year"),
                        "publication_count": indicator.get("publication_count", 0),
                        "citation_count": indicator.get("citation_count", 0),
                        "citations_per_paper": indicator.get("citations_per_paper", 0.0),
                        "international_collaboration_rate": indicator.get("international_collaboration_rate", 0.0),
                        "quality_proxy": indicator.get("quality_proxy", 0.0),
                        "productivity_proxy": indicator.get("productivity_proxy", 0.0),
                        "h_index": indicator.get("h_index", 0),
                        "top_percentile_citations": indicator.get("top_percentile_citations", 0.0)
                    }
                )
                conn.commit()
    
    logger.info("Raw metrics loaded")


def load_normalized_metrics(normalized_indicators: List[Dict], institution_map: Dict[str, int]) -> None:
    """Load normalized metrics into database."""
    logger.info(f"Loading {len(normalized_indicators)} normalized metric records...")
    
    engine = create_db_engine()
    
    with engine.connect() as conn:
        for metric in normalized_indicators:
            canonical_name = metric.get("canonical_name")
            institution_id = institution_map.get(canonical_name)
            
            if not institution_id:
                continue
            
            check_query = text("""
                SELECT metric_id FROM normalized_metrics 
                WHERE institution_id = :institution_id AND year = :year
            """)
            result = conn.execute(
                check_query,
                {
                    "institution_id": institution_id,
                    "year": metric.get("year")
                }
            ).fetchone()
            
            if not result:
                insert_query = text("""
                    INSERT INTO normalized_metrics 
                    (institution_id, year, publication_score, citation_score, collaboration_score,
                     quality_score, subject_strength_score, productivity_score, normalization_method)
                    VALUES (:institution_id, :year, :publication_score, :citation_score, :collaboration_score,
                            :quality_score, :subject_strength_score, :productivity_score, :normalization_method)
                """)
                conn.execute(
                    insert_query,
                    {
                        "institution_id": institution_id,
                        "year": metric.get("year"),
                        "publication_score": metric.get("publication_score", 0.0),
                        "citation_score": metric.get("citation_score", 0.0),
                        "collaboration_score": metric.get("collaboration_score", 0.0),
                        "quality_score": metric.get("quality_score", 0.0),
                        "subject_strength_score": metric.get("subject_strength_score", 0.0),
                        "productivity_score": metric.get("productivity_score", 0.0),
                        "normalization_method": NORMALIZATION_METHOD
                    }
                )
                conn.commit()
    
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
        from scripts.normalize_metrics import load_normalized_metrics
        normalized = load_normalized_metrics()
        if normalized:
            load_normalized_metrics(normalized, institution_map)
    
    # Load methodology weights
    load_methodology_weights()
    
    logger.info("Database loading complete")
