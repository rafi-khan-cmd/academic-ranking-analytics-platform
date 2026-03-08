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


def load_institution_resolution(resolved_institutions: List[Dict], institution_map: Dict[str, int]) -> None:
    """Load institution resolution records into database."""
    logger.info(f"Loading {len(resolved_institutions)} institution resolution records...")
    
    engine = create_db_engine()
    
    with engine.connect() as conn:
        for inst in resolved_institutions:
            openalex_id = inst.get("openalex_id")
            canonical_name = inst.get("canonical_name")
            institution_id = institution_map.get(canonical_name)
            
            # Check if resolution already exists
            check_query = text("""
                SELECT resolution_id FROM institution_resolution 
                WHERE openalex_id = :openalex_id
            """)
            result = conn.execute(check_query, {"openalex_id": openalex_id}).fetchone()
            
            if not result:
                insert_query = text("""
                    INSERT INTO institution_resolution 
                    (institution_id, openalex_id, openalex_name, ror_id, resolved_name, 
                     canonical_name, match_method, match_confidence, country)
                    VALUES (:institution_id, :openalex_id, :openalex_name, :ror_id, :resolved_name,
                            :canonical_name, :match_method, :match_confidence, :country)
                """)
                conn.execute(
                    insert_query,
                    {
                        "institution_id": institution_id,
                        "openalex_id": openalex_id,
                        "openalex_name": inst.get("institution_name"),
                        "ror_id": inst.get("ror_id"),
                        "resolved_name": inst.get("canonical_name"),
                        "canonical_name": canonical_name,
                        "match_method": inst.get("match_method", "none"),
                        "match_confidence": inst.get("match_confidence", 0.0),
                        "country": inst.get("country")
                    }
                )
                conn.commit()
    
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
    logger.info("Loading works...")
    
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
