"""
Crossref enrichment module for DOI-based publication metadata enrichment.
Optional enrichment layer for works that have DOIs.
"""

import requests
import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from urllib.parse import quote

from scripts.config import CROSSREF_BASE_URL, CROSSREF_MAILTO, RAW_DATA_DIR

logger = logging.getLogger(__name__)

# Rate limiting
CROSSREF_RATE_LIMIT_DELAY = 0.5
CROSSREF_MAX_RETRIES = 3


def get_crossref_headers() -> Dict[str, str]:
    """Get headers for Crossref API requests."""
    headers = {
        "Accept": "application/json",
        "User-Agent": f"AcademicRankingsPlatform/1.0 (mailto:{CROSSREF_MAILTO})" if CROSSREF_MAILTO else "AcademicRankingsPlatform/1.0"
    }
    return headers


def enrich_work_by_doi(doi: str) -> Optional[Dict[str, Any]]:
    """
    Enrich work metadata using Crossref API by DOI.
    
    Args:
        doi: DOI string (with or without https://doi.org/ prefix)
    
    Returns:
        Enriched metadata dictionary or None if failed
    """
    # Clean DOI
    if doi.startswith("https://doi.org/"):
        doi = doi.replace("https://doi.org/", "")
    elif doi.startswith("doi:"):
        doi = doi.replace("doi:", "")
    
    doi = doi.strip()
    if not doi:
        return None
    
    url = f"{CROSSREF_BASE_URL}/works/{quote(doi)}"
    headers = get_crossref_headers()
    
    for attempt in range(CROSSREF_MAX_RETRIES):
        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            # Extract useful fields
            enriched = {
                "doi": data.get("DOI"),
                "title": data.get("title", [None])[0] if data.get("title") else None,
                "published_date": data.get("published-print", {}).get("date-parts", [None])[0] if data.get("published-print") else None,
                "journal": data.get("container-title", [None])[0] if data.get("container-title") else None,
                "publisher": data.get("publisher"),
                "type": data.get("type"),
                "funder": data.get("funder"),
                "subject": data.get("subject", []),
                "raw_crossref": data  # Keep full response for reference
            }
            
            return enriched
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.debug(f"DOI not found in Crossref: {doi}")
                return None
            elif e.response.status_code == 429:
                wait_time = (attempt + 1) * 2
                logger.warning(f"Rate limited. Waiting {wait_time}s...")
                time.sleep(wait_time)
                continue
            logger.warning(f"HTTP error for DOI {doi}: {e.response.status_code}")
            return None
            
        except requests.exceptions.RequestException as e:
            if attempt < CROSSREF_MAX_RETRIES - 1:
                time.sleep(1)
                continue
            logger.warning(f"Request failed for DOI {doi}: {e}")
            return None
    
    return None


def enrich_works_batch(works: List[Dict[str, Any]], max_enrichments: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Enrich a batch of works with Crossref metadata.
    
    Args:
        works: List of work dictionaries (must have 'doi' field)
        max_enrichments: Maximum number of works to enrich (None = all)
    
    Returns:
        List of enriched work dictionaries
    """
    enriched_works = []
    enriched_count = 0
    
    for work in works:
        doi = work.get("doi")
        if not doi:
            enriched_works.append(work)
            continue
        
        if max_enrichments and enriched_count >= max_enrichments:
            enriched_works.append(work)
            continue
        
        enriched_data = enrich_work_by_doi(doi)
        if enriched_data:
            # Merge enrichment data into work
            work["crossref_enrichment"] = enriched_data
            enriched_count += 1
        
        enriched_works.append(work)
        time.sleep(CROSSREF_RATE_LIMIT_DELAY)
    
    logger.info(f"Enriched {enriched_count} works with Crossref metadata")
    return enriched_works


def save_enriched_works(works: List[Dict[str, Any]], filename: str = "works_crossref_enriched.json") -> None:
    """Save enriched works to JSON file."""
    filepath = RAW_DATA_DIR / filename
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(works, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved {len(works)} enriched works to {filepath}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Example usage
    test_works = [
        {"doi": "10.1038/nature12373", "title": "Test work"},
        {"doi": "10.1126/science.1234567", "title": "Another test"}
    ]
    enriched = enrich_works_batch(test_works)
    logger.info(f"Enriched {len(enriched)} works")
