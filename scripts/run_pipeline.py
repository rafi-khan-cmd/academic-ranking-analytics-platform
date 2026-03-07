"""
Main data pipeline orchestrator.
Runs the complete data pipeline from API extraction to database loading.
"""

import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.extract_data import extract_top_institutions, fetch_institution_works_batch, save_raw_data
from scripts.clean_data import clean_institution_data, save_cleaned_data
from scripts.resolve_entities import resolve_institution_entities, save_resolved_entities
from scripts.build_indicators import build_indicators_from_resolved_entities, save_indicators
from scripts.normalize_metrics import normalize_indicators, save_normalized_metrics
from scripts.load_to_postgres import (
    initialize_database, load_institutions, load_methodology_weights,
    load_raw_metrics, load_normalized_metrics
)
from scripts.ranking_engine import compute_all_methodology_rankings
from scripts.advanced_analytics import (
    compute_feature_importance, compute_institution_clusters,
    save_clusters_to_db, compute_sensitivity_analysis, save_sensitivity_to_db
)
from scripts.config import DEFAULT_YEAR

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_complete_pipeline(
    top_n_institutions: int = 200,
    fetch_works: bool = True,
    year: int = DEFAULT_YEAR
):
    """
    Run the complete data pipeline from API extraction to analytics.
    
    Args:
        top_n_institutions: Number of top institutions to fetch
        fetch_works: Whether to fetch works/publication data (takes longer)
        year: Year for analysis
    """
    logger.info("=" * 70)
    logger.info("ACADEMIC RANKINGS ANALYTICS PLATFORM - DATA PIPELINE")
    logger.info("=" * 70)
    logger.info(f"Fetching top {top_n_institutions} institutions from OpenAlex API")
    logger.info(f"Year: {year}")
    logger.info("=" * 70)
    
    try:
        # Phase 1: Data Extraction
        logger.info("\n[PHASE 1] Extracting institutions from OpenAlex API...")
        institutions = extract_top_institutions(top_n=top_n_institutions)
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
        
        # Phase 4: Fetch Works Data (Optional but recommended)
        works_data_map = None
        if fetch_works:
            logger.info("\n[PHASE 4] Fetching works/publication data from OpenAlex API...")
            logger.info("This may take 10-30 minutes depending on number of institutions...")
            
            institution_ids = [inst.get("openalex_id") for inst in resolved if inst.get("openalex_id")]
            works_data_map = fetch_institution_works_batch(
                institution_ids,
                year=year,
                limit_per_institution=500  # Limit to avoid excessive API calls
            )
            logger.info(f"✓ Fetched works data for {len(works_data_map)} institutions")
        else:
            logger.info("\n[PHASE 4] Skipping works data fetch (use fetch_works=True for full data)")
        
        # Phase 5: Indicator Engineering
        logger.info("\n[PHASE 5] Building indicators from works data...")
        indicators = build_indicators_from_resolved_entities(resolved, works_data_map=works_data_map)
        save_indicators(indicators)
        logger.info(f"✓ Built indicators for {len(indicators)} institutions")
        
        # Phase 6: Normalization
        logger.info("\n[PHASE 6] Normalizing metrics...")
        normalized = normalize_indicators(indicators)
        save_normalized_metrics(normalized)
        logger.info(f"✓ Normalized {len(normalized)} metric records")
        
        # Phase 7: Database Loading
        logger.info("\n[PHASE 7] Loading data to PostgreSQL...")
        initialize_database()
        institution_map = load_institutions(resolved)
        load_methodology_weights()
        load_raw_metrics(indicators, institution_map)
        load_normalized_metrics(normalized, institution_map)
        logger.info("✓ Data loaded to database")
        
        # Phase 8: Ranking Computation
        logger.info("\n[PHASE 8] Computing rankings for all methodologies...")
        compute_all_methodology_rankings(year=year)
        logger.info("✓ Rankings computed")
        
        # Phase 9: Advanced Analytics
        logger.info("\n[PHASE 9] Running advanced analytics...")
        
        # Feature importance
        logger.info("  - Computing feature importance...")
        importance = compute_feature_importance(year=year)
        logger.info(f"    ✓ Feature importance computed: {len(importance)} indicators")
        
        # Clustering
        logger.info("  - Computing institution clusters...")
        clusters = compute_institution_clusters(n_clusters=4, year=year)
        if clusters:
            save_clusters_to_db(clusters)
            logger.info(f"    ✓ Clustered {len(clusters)} institutions")
        
        # Sensitivity analysis
        logger.info("  - Computing sensitivity analysis...")
        sensitivity = compute_sensitivity_analysis(year=year)
        if sensitivity:
            save_sensitivity_to_db(sensitivity, year=year)
            logger.info(f"    ✓ Sensitivity computed for {len(sensitivity)} institutions")
        
        logger.info("\n" + "=" * 70)
        logger.info("PIPELINE COMPLETE!")
        logger.info("=" * 70)
        logger.info(f"✓ {len(resolved)} institutions processed")
        logger.info(f"✓ Rankings computed for {len(indicators)} institutions")
        logger.info(f"✓ Advanced analytics completed")
        logger.info("\nNext steps:")
        logger.info("1. Start dashboard: streamlit run dashboard/app.py")
        logger.info("2. View results in PostgreSQL database")
        logger.info("=" * 70)
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        raise


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
        "--year",
        type=int,
        default=DEFAULT_YEAR,
        help=f"Year for analysis (default: {DEFAULT_YEAR})"
    )
    
    args = parser.parse_args()
    
    run_complete_pipeline(
        top_n_institutions=args.institutions,
        fetch_works=not args.no_works,
        year=args.year
    )
