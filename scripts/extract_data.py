"""
Production data extraction module for OpenAlex API.
Handles API requests, rate limiting, caching, retry/backoff, and checkpointing.
"""

import requests
import json
import time
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from tqdm import tqdm
from datetime import datetime, timedelta
import hashlib

from scripts.config import (
    OPENALEX_BASE_URL, OPENALEX_EMAIL, OPENALEX_API_KEY,
    RAW_DATA_DIR, DEFAULT_YEARS_BACK
)

logger = logging.getLogger(__name__)

# Import works aggregator for streaming processing (REQUIRED)
try:
    from scripts.works_aggregator import (
        create_institution_metrics_accumulator,
        process_works_page,
        finalize_institution_metrics,
        MAX_WORKS_PER_INSTITUTION
    )
except ImportError as e:
    # Streaming aggregation is REQUIRED - fail if not available
    logger.error(f"CRITICAL: works_aggregator module not available: {e}")
    logger.error("Streaming aggregation is required for memory-efficient processing.")
    raise RuntimeError("works_aggregator module is required but not available") from e

# Ensure data directory exists
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR = RAW_DATA_DIR / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Rate limiting configuration
RATE_LIMIT_DELAY = 0.5  # Seconds between requests
MAX_RETRIES = 3
RETRY_BACKOFF = [1, 2, 4]  # Seconds to wait before retry


def get_openalex_headers() -> Dict[str, str]:
    """Get headers for OpenAlex API requests."""
    headers = {
        "Accept": "application/json",
        "User-Agent": f"AcademicRankingsPlatform/1.0 (mailto:{OPENALEX_EMAIL})" if OPENALEX_EMAIL else "AcademicRankingsPlatform/1.0"
    }
    if OPENALEX_API_KEY:
        headers["Authorization"] = f"Bearer {OPENALEX_API_KEY}"
    return headers


def get_cache_key(url: str, params: Dict) -> str:
    """Generate cache key from URL and parameters."""
    cache_str = f"{url}?{json.dumps(params, sort_keys=True)}"
    return hashlib.md5(cache_str.encode()).hexdigest()


def get_cached_response(cache_key: str) -> Optional[Dict[str, Any]]:
    """Get cached API response if available."""
    cache_file = CACHE_DIR / f"{cache_key}.json"
    if cache_file.exists():
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Check if cache is still valid (24 hours)
                cache_time = datetime.fromisoformat(data.get("cached_at", "2000-01-01"))
                if datetime.now() - cache_time < timedelta(hours=24):
                    return data.get("response")
        except Exception as e:
            logger.debug(f"Cache read error: {e}")
    return None


def cache_response(cache_key: str, response: Dict[str, Any]) -> None:
    """Cache API response."""
    cache_file = CACHE_DIR / f"{cache_key}.json"
    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump({
                "cached_at": datetime.now().isoformat(),
                "response": response
            }, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.debug(f"Cache write error: {e}")


def make_request_with_retry(url: str, params: Dict = None, use_cache: bool = True) -> Optional[Dict[str, Any]]:
    """
    Make API request with retry logic and caching.
    
    Args:
        url: API endpoint URL
        params: Query parameters
        use_cache: Whether to use cached responses
    
    Returns:
        JSON response or None if failed
    """
    params = params or {}
    
    # Add API key to params (OpenAlex accepts it as query parameter)
    if OPENALEX_API_KEY:
        params["api_key"] = OPENALEX_API_KEY
    
    cache_key = get_cache_key(url, params)
    
    # Check cache first
    if use_cache:
        cached = get_cached_response(cache_key)
        if cached:
            return cached
    
    headers = get_openalex_headers()
    
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # Cache successful response
            if use_cache:
                cache_response(cache_key, data)
            
            return data
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:  # Rate limited
                wait_time = RETRY_BACKOFF[attempt] * 2
                logger.warning(f"Rate limited. Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
                continue
            elif e.response.status_code >= 500:  # Server error
                if attempt < MAX_RETRIES - 1:
                    wait_time = RETRY_BACKOFF[attempt]
                    logger.warning(f"Server error {e.response.status_code}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
            logger.error(f"HTTP error {e.response.status_code}: {e}")
            return None
            
        except requests.exceptions.RequestException as e:
            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_BACKOFF[attempt]
                logger.warning(f"Request error: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue
            logger.error(f"Request failed after {MAX_RETRIES} attempts: {e}")
            return None
    
    return None


def fetch_institutions_by_filter(
    filters: Dict[str, Any],
    sort_by: str = "cited_by_count:desc",
    per_page: int = 100,  # OpenAlex max per_page is 100
    max_results: int = 500,
    use_cache: bool = True
) -> List[Dict[str, Any]]:
    """
    Fetch institutions using OpenAlex API filters with pagination.
    
    Args:
        filters: Dictionary of filter parameters
        sort_by: Sort parameter
        per_page: Results per page (max 100 for OpenAlex)
        max_results: Maximum total results
        use_cache: Whether to use cached responses
    
    Returns:
        List of institution records
    """
    url = f"{OPENALEX_BASE_URL}/institutions"
    all_results = []
    page = 1
    
    # Ensure per_page doesn't exceed OpenAlex limit
    per_page = min(per_page, 100)
    
    # Build filter string
    filter_parts = []
    for key, value in filters.items():
        if value:
            filter_parts.append(f"{key}:{value}")
    filter_str = ",".join(filter_parts) if filter_parts else None
    
    # Debug logging: Log exact params being used
    logger.info(f"Fetching institutions (max {max_results})...")
    logger.debug(f"OpenAlex request params: filter={filter_str}, sort={sort_by}, per_page={per_page}, api_key={'***' if OPENALEX_API_KEY else 'NOT SET'}")
    
    while len(all_results) < max_results:
        params = {
            "per_page": min(per_page, max_results - len(all_results)),
            "page": page,
            "sort": sort_by
        }
        
        if filter_str:
            params["filter"] = filter_str
        
        data = make_request_with_retry(url, params=params, use_cache=use_cache)
        if not data:
            logger.warning(f"No data returned from OpenAlex API for page {page}")
            break
        
        results = data.get("results", [])
        
        # Debug logging: Log first response details
        if page == 1:
            logger.info(f"First response: {len(results)} institutions returned")
            if results:
                sample_inst = results[0]
                logger.debug(f"Sample institution: type={sample_inst.get('type')}, cited_by_count={sample_inst.get('cited_by_count')}, name={sample_inst.get('display_name', 'N/A')[:50]}")
            else:
                logger.warning(f"First response returned 0 results. Response keys: {list(data.keys())}")
                logger.debug(f"Full response shape: {type(data)}, keys: {list(data.keys()) if isinstance(data, dict) else 'not a dict'}")
        
        if not results:
            logger.info(f"No more results at page {page}")
            break
        
        all_results.extend(results)
        logger.info(f"Fetched {len(all_results)} institutions...")
        
        # Check if there are more pages
        if len(results) < per_page:
            break
        
        page += 1
        time.sleep(RATE_LIMIT_DELAY)
    
    logger.info(f"Fetched {len(all_results)} institutions total")
    if len(all_results) == 0:
        logger.error("WARNING: 0 institutions fetched. Check OpenAlex API key and filters.")
    return all_results


def extract_top_institutions(
    top_n: int = 200,
    min_cited_by_count: int = 1000,
    countries: Optional[List[str]] = None,
    institution_types: Optional[List[str]] = None,
    use_cache: bool = True
) -> List[Dict[str, Any]]:
    """
    Extract top institutions from OpenAlex API based on citation counts.
    
    Args:
        top_n: Number of top institutions to fetch
        min_cited_by_count: Minimum citation count threshold
        countries: Optional list of country codes to filter
        institution_types: Optional list of institution types (e.g., ["education", "company"])
        use_cache: Whether to use cached responses
    
    Returns:
        List of top institution records
    """
    logger.info(f"Extracting top {top_n} institutions from OpenAlex API...")
    
    # Build filters
    filters = {
        "cited_by_count": f">{min_cited_by_count}"
    }
    
    # Institution type filtering - support education and other valid types
    if institution_types:
        type_filter = "|".join(institution_types)
        filters["type"] = type_filter
        logger.info(f"Using custom institution types filter: {type_filter}")
    else:
        # Default: include education (most common for universities) and other academic types
        # Don't restrict too much - let OpenAlex return what it has
        filters["type"] = "education|company|facility"  # education covers universities
        logger.info("Using default institution type filter: education|company|facility")
    
    if countries:
        country_filter = "|".join(countries)
        filters["country_code"] = country_filter
        logger.info(f"Filtering by countries: {country_filter}")
    
    # Debug: Log filter being used
    logger.debug(f"OpenAlex filters: {filters}")
    
    # Fetch institutions
    institutions = fetch_institutions_by_filter(
        filters=filters,
        sort_by="cited_by_count:desc",
        per_page=100,  # OpenAlex max is 100
        max_results=top_n * 2,  # Fetch more to filter
        use_cache=use_cache
    )
    
    logger.info(f"Received {len(institutions)} institutions from OpenAlex API")
    
    # Don't post-filter by type - accept all types returned by OpenAlex
    # The API filter already handled type selection
    filtered = institutions
    
    # Sort by cited_by_count - use top-level field, not summary_stats
    # OpenAlex institutions have cited_by_count at top level
    filtered.sort(
        key=lambda x: x.get("cited_by_count", 0) or x.get("summary_stats", {}).get("cited_by_count", 0),
        reverse=True
    )
    
    top_institutions = filtered[:top_n]
    
    # Debug: Log what types we got
    if top_institutions:
        type_counts = {}
        for inst in top_institutions:
            inst_type = inst.get("type", "unknown")
            type_counts[inst_type] = type_counts.get(inst_type, 0) + 1
        logger.info(f"Institution types in top {len(top_institutions)}: {type_counts}")
    
    logger.info(f"Selected top {len(top_institutions)} institutions")
    
    if len(top_institutions) == 0:
        logger.error("ERROR: 0 institutions selected. Check OpenAlex API response and filters.")
    
    # Save raw data
    save_raw_data(top_institutions, "institutions_raw.json")
    
    return top_institutions


def fetch_institution_works_streaming(
    institution_id: str,
    year: Optional[int] = None,
    years_back: int = DEFAULT_YEARS_BACK,
    per_page: int = 100,
    max_works: int = MAX_WORKS_PER_INSTITUTION,
    use_cache: bool = True,
    accumulator: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Fetch and aggregate works for an institution using TRUE streaming processing.
    
    Processes works page-by-page and accumulates only essential metrics,
    keeping memory usage constant instead of growing with each page.
    
    NEVER accumulates full work objects - processes and discards immediately.
    
    Args:
        institution_id: OpenAlex institution ID
        year: Specific year (if None, uses years_back)
        years_back: Number of years back from current year
        per_page: Results per page (max 100)
        max_works: Maximum works to process before truncating
        use_cache: Whether to use cached responses
        accumulator: Optional existing accumulator to update
    
    Returns:
        Aggregated metrics dictionary (not full work list)
    """
    if accumulator is None:
        accumulator = create_institution_metrics_accumulator(institution_id)
    
    url = f"{OPENALEX_BASE_URL}/works"
    page = 1
    
    # Ensure per_page doesn't exceed OpenAlex limit
    per_page = min(per_page, 100)
    
    # Build year filter
    if year:
        year_filter = f"publication_year:{year}"
    else:
        current_year = datetime.now().year
        start_year = current_year - years_back
        year_filter = f"publication_year:>{start_year}"
    
    filter_str = f"institutions.id:{institution_id},{year_filter}"
    
    logger.info(
        f"Processing works for institution {institution_id} "
        f"(max_works={max_works}, per_page={per_page})..."
    )
    
    stop_reason = None
    
    while True:
        # Check if we've hit the cap BEFORE fetching next page
        if accumulator["works_processed"] >= max_works:
            logger.warning(
                f"Hit max works cap for institution {institution_id}, "
                f"truncating at {max_works} works (processed: {accumulator['works_processed']})"
            )
            accumulator["truncated"] = True
            stop_reason = "hit_cap"
            break
        
        params = {
            "filter": filter_str,
            "per_page": per_page,
            "page": page
        }
        
        data = make_request_with_retry(url, params=params, use_cache=use_cache)
        if not data:
            logger.debug(f"No data returned for institution {institution_id}, page {page}")
            stop_reason = "api_empty_page"
            break
        
        # Safe extraction with defensive handling
        works_page = data.get("results", [])
        
        # Protect against None or non-list responses
        if works_page is None:
            logger.warning(f"OpenAlex returned null results for institution {institution_id}, page {page}")
            works_page = []
            stop_reason = "api_null_results"
            break
        
        if not isinstance(works_page, list):
            logger.warning(
                f"Unexpected works_page format for institution {institution_id}, page {page}: "
                f"expected list, got {type(works_page)}"
            )
            stop_reason = "api_unexpected_format"
            break
        
        if not works_page:
            logger.debug(f"No works in page {page} for institution {institution_id}")
            stop_reason = "pagination_exhausted"
            break
        
        # Store works_processed before processing to detect if cap was hit during processing
        works_before = accumulator["works_processed"]
        was_truncated_before = accumulator.get("truncated", False)
        
        # CRITICAL: Process this page immediately and discard raw work objects
        # This is the true streaming step - never accumulate full works
        process_works_page(accumulator, works_page, max_works=max_works)
        
        # Log progress
        works_count = len(works_page)
        logger.info(
            f"Fetched page {page} for {institution_id}: "
            f"{works_count} works in page, {accumulator['works_processed']} total processed "
            f"(cap: {max_works})"
        )
        
        # Check if cap was hit during processing (truncated flag changed from False to True)
        cap_hit_during_processing = accumulator.get("truncated", False) and not was_truncated_before
        
        # Check if there are more pages BEFORE clearing reference
        if works_count < per_page:
            # Natural end - no more pages available
            # Only mark as truncated if we actually hit the cap during processing
            if cap_hit_during_processing:
                logger.warning(
                    f"Institution {institution_id} hit cap during page processing: "
                    f"{accumulator['works_processed']} works (cap: {max_works})"
                )
                stop_reason = "hit_cap"
            else:
                # Natural end - clear truncated flag if it was incorrectly set
                accumulator["truncated"] = False
                stop_reason = "end_of_results"
            break
        
        # Explicitly clear reference to help GC (after we're done with it)
        works_page = None
        
        page += 1
        time.sleep(RATE_LIMIT_DELAY)
        
        # Check cap again after processing - but only mark truncated if we actually stopped due to cap
        # If we naturally finished (no more pages), truncated flag should already be False
        if accumulator["works_processed"] >= max_works:
            # Check if we hit the cap during processing
            if cap_hit_during_processing:
                # Cap was hit during processing, already marked as truncated
                stop_reason = "hit_cap"
                break
            # Otherwise continue to next page if available
    
    # Log completion with stop reason
    if stop_reason is None:
        stop_reason = "unknown"
    
    logger.info(
        f"Completed streaming aggregation for {institution_id}: "
        f"{accumulator['works_processed']} works processed "
        f"(stopped: {stop_reason}, cap: {max_works}), "
        f"accumulator size remains compact (no full works stored)"
    )
    
    return accumulator


def fetch_institution_works(
    institution_id: str,
    year: Optional[int] = None,
    years_back: int = DEFAULT_YEARS_BACK,
    per_page: int = 100,
    limit: Optional[int] = None,
    use_cache: bool = True
) -> List[Dict[str, Any]]:
    """
    ⚠️ DEPRECATED - DO NOT USE ⚠️
    
    Legacy function that accumulates full works in memory.
    This function WILL cause memory exhaustion for large institutions.
    
    Use fetch_institution_works_streaming() instead for memory-efficient processing.
    
    This function is kept ONLY for backward compatibility with old code.
    The main pipeline does NOT use this function.
    """
    url = f"{OPENALEX_BASE_URL}/works"
    all_works = []
    page = 1
    
    per_page = min(per_page, 100)
    
    if year:
        year_filter = f"publication_year:{year}"
    else:
        current_year = datetime.now().year
        start_year = current_year - years_back
        year_filter = f"publication_year:>{start_year}"
    
    filter_str = f"institutions.id:{institution_id},{year_filter}"
    
    logger.debug(f"Fetching works for institution {institution_id}...")
    
    while True:
        if limit and len(all_works) >= limit:
            break
        
        params = {
            "filter": filter_str,
            "per_page": per_page,
            "page": page
        }
        
        data = make_request_with_retry(url, params=params, use_cache=use_cache)
        if not data:
            break
        
        works = data.get("results", [])
        if not works:
            break
        
        all_works.extend(works)
        
        if len(works) < per_page:
            break
        
        page += 1
        time.sleep(RATE_LIMIT_DELAY)
        
        if limit and len(all_works) >= limit:
            all_works = all_works[:limit]
            break
    
    logger.debug(f"Fetched {len(all_works)} works for institution {institution_id}")
    return all_works


def fetch_institution_works_batch(
    institution_ids: List[str],
    year: Optional[int] = None,
    years_back: int = DEFAULT_YEARS_BACK,
    limit_per_institution: int = 200,  # Reduced default, capped at MAX_WORKS_PER_INSTITUTION
    use_cache: bool = True,
    checkpoint_file: Optional[Path] = None
) -> Dict[str, Dict[str, Any]]:
    """
    Fetch and aggregate works for multiple institutions using TRUE streaming processing.
    
    Uses memory-efficient streaming aggregation instead of accumulating full work lists.
    Returns aggregated metrics dictionary instead of full works lists.
    
    NEVER accumulates full work objects - processes page-by-page and discards immediately.
    
    Args:
        institution_ids: List of OpenAlex institution IDs
        year: Optional specific year
        years_back: Number of years back from current year
        limit_per_institution: Maximum works per institution (capped at MAX_WORKS_PER_INSTITUTION)
        use_cache: Whether to use cached responses
        checkpoint_file: Optional path to checkpoint file for resuming
    
    Returns:
        Dictionary mapping institution_id to aggregated metrics (NOT full work lists)
    """
    logger.info(f"Fetching works for {len(institution_ids)} institutions (TRUE streaming mode)...")
    
    # Cap limit_per_institution at MAX_WORKS_PER_INSTITUTION
    limit_per_institution = min(limit_per_institution, MAX_WORKS_PER_INSTITUTION)
    logger.info(f"Using max works cap: {MAX_WORKS_PER_INSTITUTION} per institution")
    
    # Load checkpoint if exists (only aggregated metrics, never full works)
    # Skip checkpoint loading if full_refresh is requested
    aggregated_metrics = {}
    processed_ids = set()
    
    # Check if we should load checkpoint (only if not full refresh and checkpoint exists)
    should_load_checkpoint = checkpoint_file and checkpoint_file.exists() and use_cache
    
    if should_load_checkpoint:
        try:
            # Check file size first - old format with full works can be huge
            file_size_mb = checkpoint_file.stat().st_size / (1024 * 1024)
            if file_size_mb > 10:  # If checkpoint > 10MB, likely old format with full works
                logger.warning(
                    f"Checkpoint file is {file_size_mb:.1f}MB - likely contains full works data. "
                    f"Ignoring old checkpoint and starting fresh to prevent memory issues."
                )
            else:
                with open(checkpoint_file, 'r', encoding='utf-8') as f:
                    checkpoint_data = json.load(f)
                    # Check checkpoint version - old format has "works" key, new has "aggregated_metrics"
                    if "works" in checkpoint_data and "aggregated_metrics" not in checkpoint_data:
                        logger.warning(
                            "Checkpoint file contains old format with full works data. "
                            "Ignoring old checkpoint and starting fresh to prevent memory issues."
                        )
                    else:
                        # New format: aggregated metrics only
                        aggregated_metrics_raw = checkpoint_data.get("aggregated_metrics", {})
                        processed_ids = set(checkpoint_data.get("processed_ids", []))
                        
                        # Sanitize checkpoint data: validate and fix truncation flags
                        aggregated_metrics = {}
                        for inst_id, metrics in aggregated_metrics_raw.items():
                            works_processed = metrics.get("works_processed", 0)
                            old_truncated = metrics.get("truncated", False)
                            
                            # Validate truncation flag: only True if works_processed >= MAX_WORKS_PER_INSTITUTION
                            validated_truncated = old_truncated and works_processed >= MAX_WORKS_PER_INSTITUTION
                            
                            # Create sanitized metrics dict
                            sanitized_metrics = dict(metrics)
                            sanitized_metrics["truncated"] = validated_truncated
                            
                            # Log if we fixed an incorrect truncation flag
                            if old_truncated and not validated_truncated:
                                logger.debug(
                                    f"Sanitized checkpoint: institution {inst_id} had incorrect truncation flag "
                                    f"(works_processed={works_processed} < {MAX_WORKS_PER_INSTITUTION})"
                                )
                            
                            aggregated_metrics[inst_id] = sanitized_metrics
                        
                        logger.info(f"Loaded existing aggregated checkpoint: {len(processed_ids)} institutions already processed")
                        logger.info("Resuming from checkpoint - skipping already processed institutions")
        except Exception as e:
            logger.warning(f"Error loading checkpoint: {e}. Starting fresh.")
    elif checkpoint_file and checkpoint_file.exists() and not use_cache:
        logger.info("Full refresh requested - ignoring existing checkpoint and starting fresh aggregation")
    else:
        logger.info("Starting fresh aggregation (no checkpoint found)")
    
    # Process each institution with TRUE streaming
    for i, inst_id in enumerate(institution_ids):
        if inst_id in processed_ids:
            logger.debug(f"Skipping {inst_id} (already processed in checkpoint)")
            continue
        
        logger.info(f"Processing works for institution {i+1}/{len(institution_ids)}: {inst_id}")
        
        # Use TRUE streaming aggregation - never accumulates full works
        accumulator = fetch_institution_works_streaming(
            inst_id,
            year=year,
            years_back=years_back,
            per_page=100,
            max_works=limit_per_institution,
            use_cache=use_cache
        )
        
        # Finalize metrics (compact aggregated structure only)
        final_metrics = finalize_institution_metrics(accumulator)
        aggregated_metrics[inst_id] = final_metrics
        processed_ids.add(inst_id)
        
        if final_metrics.get("truncated"):
            logger.warning(
                f"Institution {inst_id} truncated at {final_metrics['works_processed']} works "
                f"(cap: {MAX_WORKS_PER_INSTITUTION})"
            )
        
        logger.info(
            f"Completed institution {i+1}/{len(institution_ids)}: "
            f"{final_metrics['works_processed']} works processed, "
            f"aggregated metrics only (no full works stored)"
        )
        
        # Save checkpoint after each institution (stores only aggregated metrics)
        if checkpoint_file:
            try:
                with open(checkpoint_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        "processed_ids": list(processed_ids),
                        "aggregated_metrics": aggregated_metrics,  # Only compact metrics, never full works
                        "checkpoint_version": "2.0"  # Mark as new format
                    }, f, indent=2, ensure_ascii=False)
            except Exception as e:
                logger.warning(f"Error saving checkpoint: {e}")
        
        # Rate limiting
        if (i + 1) % 10 == 0:
            time.sleep(1)
        else:
            time.sleep(RATE_LIMIT_DELAY)
    
    # Save final checkpoint (only aggregated metrics)
    if checkpoint_file:
        try:
            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "processed_ids": list(processed_ids),
                    "aggregated_metrics": aggregated_metrics,
                    "checkpoint_version": "2.0"
                }, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Error saving final checkpoint: {e}")
    
    # Save aggregated metrics (much smaller than full works - KBs not GBs)
    save_raw_data(
        [{"institution_id": k, "metrics": v} for k, v in aggregated_metrics.items()],
        "institution_works_aggregated.json"
    )
    
    total_works = sum(m.get("works_processed", 0) for m in aggregated_metrics.values())
    
    # Only count institutions that actually hit the cap (works_processed >= MAX_WORKS_PER_INSTITUTION)
    truly_truncated = [
        (inst_id, m) for inst_id, m in aggregated_metrics.items()
        if m.get("works_processed", 0) >= MAX_WORKS_PER_INSTITUTION
    ]
    truncated_count = len(truly_truncated)
    
    logger.info(
        f"Completed TRUE streaming works aggregation for {len(aggregated_metrics)} institutions: "
        f"{total_works:,} total works processed, "
        f"memory usage remains constant (aggregated metrics only)"
    )
    if truncated_count > 0:
        logger.warning(
            f"{truncated_count} institutions hit the {MAX_WORKS_PER_INSTITUTION:,} works cap: "
            f"{', '.join([inst_id for inst_id, _ in truly_truncated[:5]])}"
            + (f" and {truncated_count - 5} more" if truncated_count > 5 else "")
        )
    
    # Return aggregated metrics ONLY - never return full works lists
    return aggregated_metrics


def fetch_topics(
    per_page: int = 100,  # OpenAlex max per_page is 100
    max_results: int = 1000,
    sort_by: str = "works_count:desc",
    use_cache: bool = True
) -> List[Dict[str, Any]]:
    """
    Fetch topics from OpenAlex API.
    
    Args:
        per_page: Results per page
        max_results: Maximum total results
        sort_by: Sort parameter
        use_cache: Whether to use cached responses
    
    Returns:
        List of topic records
    """
    url = f"{OPENALEX_BASE_URL}/topics"
    all_topics = []
    page = 1
    
    # Ensure per_page doesn't exceed OpenAlex limit
    per_page = min(per_page, 100)
    
    logger.info(f"Fetching topics (max {max_results})...")
    
    while len(all_topics) < max_results:
        params = {
            "per_page": min(per_page, max_results - len(all_topics)),
            "page": page,
            "sort": sort_by
        }
        
        data = make_request_with_retry(url, params=params, use_cache=use_cache)
        if not data:
            break
        
        results = data.get("results", [])
        if not results:
            break
        
        all_topics.extend(results)
        logger.info(f"Fetched {len(all_topics)} topics...")
        
        if len(results) < per_page:
            break
        
        page += 1
        time.sleep(RATE_LIMIT_DELAY)
    
    logger.info(f"Fetched {len(all_topics)} topics total")
    return all_topics


def save_raw_data(data: List[Dict[str, Any]], filename: str) -> None:
    """Save raw data to JSON file."""
    filepath = RAW_DATA_DIR / filename
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved {len(data)} records to {filepath}")


def load_raw_data(filename: str) -> List[Dict[str, Any]]:
    """Load raw data from JSON file."""
    filepath = RAW_DATA_DIR / filename
    if not filepath.exists():
        logger.warning(f"File not found: {filepath}")
        return []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    institutions = extract_top_institutions(top_n=200)
    logger.info(f"Extracted {len(institutions)} institutions")
