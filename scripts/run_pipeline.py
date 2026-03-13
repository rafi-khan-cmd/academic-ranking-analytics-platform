"""
Main data pipeline orchestrator.
Runs the complete data pipeline from API extraction to database loading.
"""

import logging
import sys
from pathlib import Path
from typing import Optional, List
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.extract_data import (
    extract_top_institutions, fetch_institution_works_batch, fetch_topics,
    save_raw_data, RAW_DATA_DIR
)
from scripts.clean_data import clean_institution_data, save_cleaned_data
from scripts.resolve_entities import resolve_institution_entities, save_resolved_entities
from scripts.enrich_crossref import enrich_works_batch as enrich_crossref_batch
from scripts.enrich_semantic_scholar import enrich_works_batch as enrich_s2_batch
from scripts.build_indicators import build_indicators_from_resolved_entities, save_indicators
from scripts.normalize_metrics import normalize_indicators, save_normalized_metrics
from scripts.load_to_postgres import (
    initialize_database, load_institutions, load_methodology_weights,
    load_raw_metrics, load_normalized_metrics, load_institution_resolution,
    load_topics, load_works, log_api_ingestion
)
from scripts.ranking_engine import compute_all_methodology_rankings
from scripts.advanced_analytics import (
    compute_feature_importance, compute_institution_clusters,
    save_clusters_to_db, compute_sensitivity_analysis, save_sensitivity_to_db
)
from scripts.database import dispose_db_engine
from scripts.config import (
    DEFAULT_YEAR, DEFAULT_YEARS_BACK, DEFAULT_INSTITUTION_COUNT,
    ENABLE_CROSSREF, ENABLE_SEMANTIC_SCHOLAR
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_complete_pipeline(
    top_n_institutions: int = DEFAULT_INSTITUTION_COUNT,
    fetch_works: bool = True,
    years_back: int = DEFAULT_YEARS_BACK,
    enable_crossref: bool = ENABLE_CROSSREF,
    enable_semantic_scholar: bool = ENABLE_SEMANTIC_SCHOLAR,
    countries: Optional[List[str]] = None,
    full_refresh: bool = False
):
    """
    Run the complete production data pipeline from API extraction to analytics.
    
    Args:
        top_n_institutions: Number of top institutions to fetch
        fetch_works: Whether to fetch works/publication data
        years_back: Number of years back from current year to fetch works
        enable_crossref: Enable Crossref enrichment (optional)
        enable_semantic_scholar: Enable Semantic Scholar enrichment (optional)
        countries: Optional list of country codes to filter institutions
        full_refresh: If True, clear cache and re-fetch all data
    """
    logger.info("=" * 70)
    logger.info("ACADEMIC RANKINGS ANALYTICS PLATFORM - PRODUCTION PIPELINE")
    logger.info("=" * 70)
    logger.info(f"Configuration:")
    logger.info(f"  - Institutions: {top_n_institutions}")
    logger.info(f"  - Years back: {years_back}")
    logger.info(f"  - Fetch works: {fetch_works}")
    logger.info(f"  - Crossref enrichment: {enable_crossref}")
    logger.info(f"  - Semantic Scholar enrichment: {enable_semantic_scholar}")
    logger.info(f"  - Countries filter: {countries or 'All'}")
    logger.info("=" * 70)
    
    # Log pipeline start
    log_id = log_api_ingestion(
        source_name="pipeline",
        entity_type="full_pipeline",
        status="running",
        config_json={
            "top_n_institutions": top_n_institutions,
            "years_back": years_back,
            "fetch_works": fetch_works,
            "enable_crossref": enable_crossref,
            "enable_semantic_scholar": enable_semantic_scholar
        }
    )
    
    try:
        # Phase 1: Institution Extraction
        logger.info("\n[PHASE 1] Extracting institutions from OpenAlex API...")
        log_api_ingestion("openalex", "institution", "running")
        institutions = extract_top_institutions(
            top_n=top_n_institutions,
            countries=countries,
            use_cache=not full_refresh
        )
        log_api_ingestion("openalex", "institution", "completed", records_fetched=len(institutions))
        logger.info(f"✓ Extracted {len(institutions)} institutions")
        
        # Phase 2: Data Cleaning
        logger.info("\n[PHASE 2] Cleaning institution data...")
        from scripts.clean_data import clean_institution_data
        cleaned_institutions = clean_institution_data(institutions)
        logger.info(f"✓ Cleaned {len(cleaned_institutions)} institution records")
        
        # Phase 3: Entity Resolution (with ROR API)
        logger.info("\n[PHASE 3] Resolving entity names with ROR API...")
        resolved = resolve_institution_entities(cleaned_institutions)
        save_resolved_entities(resolved)
        logger.info(f"✓ Resolved {len(resolved)} entities")
        
        # Phase 4: Topics Extraction
        logger.info("\n[PHASE 4] Extracting topics from OpenAlex API...")
        log_api_ingestion("openalex", "topic", "running")
        topics = fetch_topics(max_results=1000, use_cache=not full_refresh)
        log_api_ingestion("openalex", "topic", "completed", records_fetched=len(topics))
        logger.info(f"✓ Extracted {len(topics)} topics")
        save_raw_data(topics, "topics_raw.json")
        
        # Phase 5: Fetch Works Data (Optional but recommended)
        # Now returns aggregated metrics instead of full works lists (TRUE streaming mode)
        aggregated_metrics_map = {}
        works_data_map = {}  # Legacy format, kept empty for compatibility
        if fetch_works:
            logger.info("\n[PHASE 5] Fetching works/publication data from OpenAlex API...")
            logger.info("Using TRUE streaming aggregation mode (memory-efficient)...")
            logger.info("This may take 10-30 minutes depending on number of institutions...")
            log_api_ingestion("openalex", "work", "running")
            
            institution_ids = [inst.get("openalex_id") for inst in resolved if inst.get("openalex_id")]
            checkpoint_file = RAW_DATA_DIR / "works_checkpoint.json"
            
            # Use MAX_WORKS_PER_INSTITUTION as default, not 200
            from scripts.works_aggregator import MAX_WORKS_PER_INSTITUTION
            aggregated_metrics_map = fetch_institution_works_batch(
                institution_ids,
                years_back=years_back,
                limit_per_institution=MAX_WORKS_PER_INSTITUTION,  # Use full cap (5000), not 200
                use_cache=not full_refresh,
                checkpoint_file=checkpoint_file
            )
            if aggregated_metrics_map:
                total_works = sum(m.get("works_processed", 0) for m in aggregated_metrics_map.values())
                log_api_ingestion("openalex", "work", "completed", records_fetched=total_works)
                logger.info(f"✓ Aggregated works data for {len(aggregated_metrics_map)} institutions ({total_works:,} total works processed)")
            else:
                aggregated_metrics_map = {}  # Ensure it's a dict, not None
                log_api_ingestion("openalex", "work", "failed", notes="No works data fetched")
                logger.warning("⚠️ No works data fetched")
        else:
            logger.info("\n[PHASE 5] Skipping works data fetch (use fetch_works=True for full data)")
            logger.info("⚠️ No works data provided; using fallback indicator path")
        
        # Phase 6: Optional Enrichment
        # NOTE: Enrichment requires full works objects, which we no longer store
        # Enrichment is skipped in streaming mode to preserve memory efficiency
        if fetch_works and aggregated_metrics_map and (enable_crossref or enable_semantic_scholar):
            logger.warning("\n[PHASE 6] Enrichment skipped in streaming mode (requires full works objects)")
            logger.info("To enable enrichment, use legacy works_data_map mode (not recommended for large datasets)")
        
        # Phase 7: Indicator Engineering
        logger.info("\n[PHASE 7] Building indicators from aggregated works metrics...")
        
        # Determine years range from years_back parameter
        # This ensures we generate indicators for all years in the requested range,
        # not just years that happen to have publications
        current_year = datetime.now().year
        start_year = current_year - years_back
        years_range = list(range(start_year, current_year + 1))
        logger.info(f"Building indicators for years range: {years_range} (years_back={years_back})")
        
        indicators = build_indicators_from_resolved_entities(
            resolved,
            works_data_map=works_data_map,  # Empty in streaming mode
            aggregated_metrics_map=aggregated_metrics_map,  # Use aggregated metrics
            years=years_range  # Explicitly pass the requested year range
        )
        save_indicators(indicators)
        logger.info(f"✓ Built indicators for {len(indicators)} institution-year records")
        
        # Phase 8: Normalization
        logger.info("\n[PHASE 8] Normalizing metrics...")
        normalized = normalize_indicators(indicators)
        save_normalized_metrics(normalized)
        logger.info(f"✓ Normalized {len(normalized)} metric records")
        
        # Phase 9: Database Loading
        logger.info("\n[PHASE 9] Loading data to PostgreSQL...")
        initialize_database()
        institution_map = load_institutions(resolved)
        load_institution_resolution(resolved, institution_map)
        topic_map = load_topics(topics)
        work_map = load_works(works_data_map, topic_map=topic_map)
        load_methodology_weights()
        load_raw_metrics(indicators, institution_map)
        load_normalized_metrics(normalized, institution_map)
        logger.info("✓ Data loaded to database")
        
        # Phase 10: Ranking Computation
        logger.info("\n[PHASE 10] Computing rankings for all methodologies...")
        
        # Extract current run's institution_ids for scoping
        current_run_institution_ids = list(institution_map.values())
        logger.info(f"Ranking scope: {len(current_run_institution_ids)} institution_ids from current pipeline run")
        
        # Compute rankings for all years found in indicators
        years_in_data = sorted(set(ind.get("year") for ind in indicators))
        for year in years_in_data:
            # Convert year to int if it's a string
            year_int = int(year) if isinstance(year, str) else year
            compute_all_methodology_rankings(
                year=year_int,
                institution_ids=current_run_institution_ids
            )
        logger.info(f"✓ Rankings computed for years: {years_in_data}")
        
        # Phase 11: Advanced Analytics
        logger.info("\n[PHASE 11] Running advanced analytics...")
        
        # Feature importance (for most recent year)
        latest_year = max(years_in_data) if years_in_data else DEFAULT_YEAR
        latest_year_int = int(latest_year) if isinstance(latest_year, str) else latest_year
        
        logger.info(f"  - Computing feature importance (year={latest_year_int})...")
        logger.info(f"    Feature importance scope: {len(current_run_institution_ids)} institutions for year {latest_year_int}")
        # Get shared engine for advanced analytics (reuse for all operations)
        from scripts.database import get_db_engine_with_retry
        analytics_engine = get_db_engine_with_retry()
        
        importance = compute_feature_importance(
            year=latest_year_int,
            institution_ids=current_run_institution_ids,
            engine=analytics_engine  # Reuse same engine
        )
        logger.info(f"    ✓ Feature importance computed: {len(importance)} indicators")
        
        # Get shared engine for all advanced analytics operations
        from scripts.database import get_db_engine_with_retry
        analytics_engine = get_db_engine_with_retry()
        
        # Clustering
        logger.info(f"  - Computing institution clusters (year={latest_year_int})...")
        logger.info(f"    Clustering scope: {len(current_run_institution_ids)} institutions for year {latest_year_int}")
        clusters = compute_institution_clusters(
            n_clusters=4,
            year=latest_year_int,
            institution_ids=current_run_institution_ids,
            engine=analytics_engine  # Reuse same engine
        )
        if clusters:
            save_clusters_to_db(clusters)
            logger.info(f"    ✓ Clustered {len(clusters)} institutions")
        
        # Sensitivity analysis
        logger.info(f"  - Computing sensitivity analysis (year={latest_year_int})...")
        logger.info(f"    Sensitivity scope: {len(current_run_institution_ids)} institutions for year {latest_year_int}")
        sensitivity = compute_sensitivity_analysis(
            year=latest_year_int,
            institution_ids=current_run_institution_ids,
            engine=analytics_engine  # Reuse same engine
        )
        if sensitivity:
            save_sensitivity_to_db(sensitivity, year=latest_year_int)
            logger.info(f"    ✓ Sensitivity computed for {len(sensitivity)} institutions")
        
        # Update pipeline log
        log_api_ingestion(
            source_name="pipeline",
            entity_type="full_pipeline",
            status="completed",
            records_fetched=len(institutions),
            records_processed=len(resolved),
            notes=f"Successfully processed {len(resolved)} institutions"
        )
        
        logger.info("\n" + "=" * 70)
        logger.info("PIPELINE COMPLETE!")
        logger.info("=" * 70)
        logger.info(f"✓ {len(resolved)} institutions processed")
        logger.info(f"✓ {len(topics)} topics extracted")
        logger.info(f"✓ {len(indicators)} indicator records computed")
        logger.info(f"✓ Rankings computed for years: {years_in_data}")
        logger.info(f"✓ Advanced analytics completed")
        logger.info("\nNext steps:")
        logger.info("1. Start dashboard: streamlit run dashboard/app.py")
        logger.info("2. View results in PostgreSQL database")
        logger.info("=" * 70)
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        log_api_ingestion(
            source_name="pipeline",
            entity_type="full_pipeline",
            status="failed",
            notes=f"Pipeline failed: {str(e)}"
        )
        raise
    finally:
        # Always dispose the shared database engine to release connections
        logger.info("Disposing database engine and releasing connections...")
        dispose_db_engine()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run Academic Rankings Analytics Platform data pipeline")
    parser.add_argument(
        "--institutions",
        type=int,
        default=200,
        help="Number of top institutions to fetch (default: 200)"
    )
    parser.add_argument(
        "--no-works",
        action="store_true",
        help="Skip fetching works data (faster but less accurate indicators)"
    )
    parser.add_argument(
        "--years-back",
        type=int,
        default=DEFAULT_YEARS_BACK,
        help=f"Number of years back to fetch works (default: {DEFAULT_YEARS_BACK})"
    )
    parser.add_argument(
        "--enable-crossref",
        action="store_true",
        help="Enable Crossref enrichment (optional)"
    )
    parser.add_argument(
        "--enable-semantic-scholar",
        action="store_true",
        help="Enable Semantic Scholar enrichment (optional)"
    )
    parser.add_argument(
        "--countries",
        type=str,
        nargs="+",
        help="Filter institutions by country codes (e.g., --countries US CA GB)"
    )
    parser.add_argument(
        "--full-refresh",
        action="store_true",
        help="Clear cache and re-fetch all data"
    )
    
    args = parser.parse_args()
    
    run_complete_pipeline(
        top_n_institutions=args.institutions,
        fetch_works=not args.no_works,
        years_back=args.years_back,
        enable_crossref=args.enable_crossref or ENABLE_CROSSREF,
        enable_semantic_scholar=args.enable_semantic_scholar or ENABLE_SEMANTIC_SCHOLAR,
        countries=args.countries,
        full_refresh=args.full_refresh
    )
