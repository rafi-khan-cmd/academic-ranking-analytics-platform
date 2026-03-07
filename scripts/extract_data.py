"""
Data extraction module for fetching institution data from OpenAlex API.
Handles API requests, rate limiting, and data persistence.
"""

import requests
import json
import time
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from tqdm import tqdm

from scripts.config import OPENALEX_BASE_URL, OPENALEX_EMAIL, RAW_DATA_DIR

logger = logging.getLogger(__name__)

# Ensure data directory exists
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)


def get_openalex_headers() -> Dict[str, str]:
    """Get headers for OpenAlex API requests."""
    headers = {
        "Accept": "application/json",
        "User-Agent": f"AcademicRankingsPlatform/1.0 (mailto:{OPENALEX_EMAIL})" if OPENALEX_EMAIL else "AcademicRankingsPlatform/1.0"
    }
    return headers


def fetch_institution_by_id(institution_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a single institution by OpenAlex ID."""
    url = f"{OPENALEX_BASE_URL}/institutions/{institution_id}"
    headers = get_openalex_headers()
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching institution {institution_id}: {e}")
        return None


def search_institutions(query: str, per_page: int = 200, max_results: int = 1000) -> List[Dict[str, Any]]:
    """Search for institutions using OpenAlex API."""
    url = f"{OPENALEX_BASE_URL}/institutions"
    headers = get_openalex_headers()
    all_results = []
    page = 1
    
    while len(all_results) < max_results:
        params = {
            "search": query,
            "per_page": min(per_page, max_results - len(all_results)),
            "page": page
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            results = data.get("results", [])
            if not results:
                break
            
            all_results.extend(results)
            
            # Check if there are more pages
            if len(results) < per_page:
                break
            
            page += 1
            time.sleep(0.5)  # Rate limiting
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error searching institutions: {e}")
            break
    
    return all_results


def fetch_institution_works(institution_id: str, year: Optional[int] = None, 
                            per_page: int = 200) -> List[Dict[str, Any]]:
    """Fetch works (publications) for an institution."""
    url = f"{OPENALEX_BASE_URL}/works"
    headers = get_openalex_headers()
    all_works = []
    page = 1
    
    filter_str = f"institutions.id:{institution_id}"
    if year:
        filter_str += f",publication_year:{year}"
    
    while True:
        params = {
            "filter": filter_str,
            "per_page": per_page,
            "page": page
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            works = data.get("results", [])
            if not works:
                break
            
            all_works.extend(works)
            
            # Check if there are more pages
            if len(works) < per_page:
                break
            
            page += 1
            time.sleep(0.5)  # Rate limiting
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching works for institution {institution_id}: {e}")
            break
    
    return all_works


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


def fetch_institutions_by_filter(filters: Dict[str, Any], sort_by: str = "cited_by_count:desc",
                                  per_page: int = 200, max_results: int = 500) -> List[Dict[str, Any]]:
    """
    Fetch institutions using OpenAlex API filters.
    
    Args:
        filters: Dictionary of filter parameters (e.g., {"type": "university", "country_code": "US"})
        sort_by: Sort parameter (e.g., "cited_by_count:desc")
        per_page: Results per page
        max_results: Maximum total results
    
    Returns:
        List of institution records
    """
    url = f"{OPENALEX_BASE_URL}/institutions"
    headers = get_openalex_headers()
    all_results = []
    page = 1
    
    # Build filter string
    filter_parts = []
    for key, value in filters.items():
        if value:
            filter_parts.append(f"{key}:{value}")
    filter_str = ",".join(filter_parts) if filter_parts else None
    
    while len(all_results) < max_results:
        params = {
            "per_page": min(per_page, max_results - len(all_results)),
            "page": page,
            "sort": sort_by
        }
        
        if filter_str:
            params["filter"] = filter_str
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            results = data.get("results", [])
            if not results:
                break
            
            all_results.extend(results)
            
            # Check if there are more pages
            if len(results) < per_page:
                break
            
            page += 1
            time.sleep(0.5)  # Rate limiting
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching institutions: {e}")
            break
    
    return all_results


def extract_top_institutions(top_n: int = 500, min_cited_by_count: int = 1000) -> List[Dict[str, Any]]:
    """
    Extract top institutions from OpenAlex API based on citation counts.
    Uses real-time API to fetch institutions sorted by research impact.
    
    Args:
        top_n: Number of top institutions to fetch
        min_cited_by_count: Minimum citation count threshold
    
    Returns:
        List of top institution records from OpenAlex
    """
    logger.info(f"Extracting top {top_n} institutions from OpenAlex API...")
    
    # Fetch institutions sorted by citation count
    # Filter for universities and research institutions
    filters = {
        "type": "university|institute|research",
        "cited_by_count": f">{min_cited_by_count}"
    }
    
    logger.info("Fetching institutions from OpenAlex API (this may take a few minutes)...")
    institutions = fetch_institutions_by_filter(
        filters=filters,
        sort_by="cited_by_count:desc",
        per_page=200,
        max_results=top_n * 2  # Fetch more to filter
    )
    
    logger.info(f"Fetched {len(institutions)} institutions from API")
    
    # Filter and sort
    # Prioritize universities and research institutions
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
    save_raw_data(top_institutions, "institutions_raw.json")
    
    return top_institutions


def fetch_institution_works_batch(institution_ids: List[str], year: Optional[int] = None,
                                   limit_per_institution: int = 1000) -> Dict[str, List[Dict[str, Any]]]:
    """
    Fetch works for multiple institutions in batch.
    
    Args:
        institution_ids: List of OpenAlex institution IDs
        year: Optional year filter
        limit_per_institution: Maximum works per institution
    
    Returns:
        Dictionary mapping institution_id to list of works
    """
    logger.info(f"Fetching works for {len(institution_ids)} institutions...")
    
    all_works = {}
    
    for i, inst_id in enumerate(tqdm(institution_ids, desc="Fetching works")):
        works = fetch_institution_works(inst_id, year=year, per_page=200)
        
        # Limit works per institution
        if len(works) > limit_per_institution:
            works = works[:limit_per_institution]
        
        all_works[inst_id] = works
        
        # Rate limiting
        if (i + 1) % 10 == 0:
            time.sleep(1)
        else:
            time.sleep(0.3)
    
    # Save works data
    save_raw_data(
        [{"institution_id": k, "works": v} for k, v in all_works.items()],
        "institution_works_raw.json"
    )
    
    return all_works


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    institutions = extract_top_institutions(top_n=500)
    logger.info(f"Extracted {len(institutions)} institutions")
