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
    per_page: int = 200,
    max_results: int = 500,
    use_cache: bool = True
) -> List[Dict[str, Any]]:
    """
    Fetch institutions using OpenAlex API filters with pagination.
    
    Args:
        filters: Dictionary of filter parameters
        sort_by: Sort parameter
        per_page: Results per page
        max_results: Maximum total results
        use_cache: Whether to use cached responses
    
    Returns:
        List of institution records
    """
    url = f"{OPENALEX_BASE_URL}/institutions"
    all_results = []
    page = 1
    
    # Build filter string
    filter_parts = []
    for key, value in filters.items():
        if value:
            filter_parts.append(f"{key}:{value}")
    filter_str = ",".join(filter_parts) if filter_parts else None
    
    logger.info(f"Fetching institutions (max {max_results})...")
    
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
            break
        
        results = data.get("results", [])
        if not results:
            break
        
        all_results.extend(results)
        logger.info(f"Fetched {len(all_results)} institutions...")
        
        # Check if there are more pages
        if len(results) < per_page:
            break
        
        page += 1
        time.sleep(RATE_LIMIT_DELAY)
    
    logger.info(f"Fetched {len(all_results)} institutions total")
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
        institution_types: Optional list of institution types
        use_cache: Whether to use cached responses
    
    Returns:
        List of top institution records
    """
    logger.info(f"Extracting top {top_n} institutions from OpenAlex API...")
    
    # Build filters
    filters = {
        "cited_by_count": f">{min_cited_by_count}"
    }
    
    if institution_types:
        type_filter = "|".join(institution_types)
        filters["type"] = type_filter
    else:
        filters["type"] = "university|institute|research"
    
    if countries:
        country_filter = "|".join(countries)
        filters["country_code"] = country_filter
    
    # Fetch institutions
    institutions = fetch_institutions_by_filter(
        filters=filters,
        sort_by="cited_by_count:desc",
        per_page=200,
        max_results=top_n * 2,  # Fetch more to filter
        use_cache=use_cache
    )
    
    # Filter and sort
    filtered = [
        inst for inst in institutions
        if inst.get("type") in ["university", "institute", "research"]
    ]
    
    # Sort by cited_by_count
    filtered.sort(
        key=lambda x: x.get("summary_stats", {}).get("cited_by_count", 0),
        reverse=True
    )
    
    top_institutions = filtered[:top_n]
    
    logger.info(f"Selected top {len(top_institutions)} institutions")
    
    # Save raw data
    save_raw_data(top_institutions, "institutions_raw.json")
    
    return top_institutions


def fetch_institution_works(
    institution_id: str,
    year: Optional[int] = None,
    years_back: int = DEFAULT_YEARS_BACK,
    per_page: int = 200,
    limit: Optional[int] = None,
    use_cache: bool = True
) -> List[Dict[str, Any]]:
    """
    Fetch works (publications) for an institution with year filtering.
    
    Args:
        institution_id: OpenAlex institution ID
        year: Specific year (if None, uses years_back)
        years_back: Number of years back from current year
        per_page: Results per page
        limit: Maximum works to fetch (None = all)
        use_cache: Whether to use cached responses
    
    Returns:
        List of work records
    """
    url = f"{OPENALEX_BASE_URL}/works"
    all_works = []
    page = 1
    
    # Build year filter
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
        
        # Check if there are more pages
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
    limit_per_institution: int = 1000,
    use_cache: bool = True,
    checkpoint_file: Optional[Path] = None
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Fetch works for multiple institutions in batch with checkpointing.
    
    Args:
        institution_ids: List of OpenAlex institution IDs
        year: Optional specific year
        years_back: Number of years back from current year
        limit_per_institution: Maximum works per institution
        use_cache: Whether to use cached responses
        checkpoint_file: Optional path to checkpoint file for resuming
    
    Returns:
        Dictionary mapping institution_id to list of works
    """
    logger.info(f"Fetching works for {len(institution_ids)} institutions...")
    
    # Load checkpoint if exists
    all_works = {}
    if checkpoint_file and checkpoint_file.exists():
        try:
            with open(checkpoint_file, 'r', encoding='utf-8') as f:
                checkpoint_data = json.load(f)
                all_works = checkpoint_data.get("works", {})
                processed_ids = set(checkpoint_data.get("processed_ids", []))
                logger.info(f"Resuming from checkpoint: {len(processed_ids)} institutions already processed")
        except Exception as e:
            logger.warning(f"Error loading checkpoint: {e}")
            processed_ids = set()
    else:
        processed_ids = set()
    
    # Process each institution
    for i, inst_id in enumerate(tqdm(institution_ids, desc="Fetching works")):
        if inst_id in processed_ids:
            continue
        
        works = fetch_institution_works(
            inst_id,
            year=year,
            years_back=years_back,
            limit=limit_per_institution,
            use_cache=use_cache
        )
        
        all_works[inst_id] = works
        processed_ids.add(inst_id)
        
        # Save checkpoint every 10 institutions
        if checkpoint_file and (i + 1) % 10 == 0:
            try:
                with open(checkpoint_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        "processed_ids": list(processed_ids),
                        "works": all_works
                    }, f, indent=2, ensure_ascii=False)
            except Exception as e:
                logger.warning(f"Error saving checkpoint: {e}")
        
        # Rate limiting
        if (i + 1) % 10 == 0:
            time.sleep(1)
        else:
            time.sleep(RATE_LIMIT_DELAY)
    
    # Save final checkpoint
    if checkpoint_file:
        try:
            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "processed_ids": list(processed_ids),
                    "works": all_works
                }, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Error saving final checkpoint: {e}")
    
    # Save works data
    save_raw_data(
        [{"institution_id": k, "works": v} for k, v in all_works.items()],
        "institution_works_raw.json"
    )
    
    logger.info(f"Fetched works data for {len(all_works)} institutions")
    return all_works


def fetch_topics(
    per_page: int = 200,
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
