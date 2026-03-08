"""
Semantic Scholar enrichment module for influence and citation metrics.
Optional enrichment layer for works that have DOIs or titles.
"""

import requests
import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from urllib.parse import quote

from scripts.config import SEMANTIC_SCHOLAR_BASE_URL, SEMANTIC_SCHOLAR_API_KEY, RAW_DATA_DIR

logger = logging.getLogger(__name__)

# Rate limiting
S2_RATE_LIMIT_DELAY = 0.5
S2_MAX_RETRIES = 3
S2_FREE_TIER_LIMIT = 100  # Free tier has rate limits


def get_s2_headers() -> Dict[str, str]:
    """Get headers for Semantic Scholar API requests."""
    headers = {
        "Accept": "application/json"
    }
    if SEMANTIC_SCHOLAR_API_KEY:
        headers["x-api-key"] = SEMANTIC_SCHOLAR_API_KEY
    return headers


def enrich_work_by_doi(doi: str) -> Optional[Dict[str, Any]]:
    """
    Enrich work metadata using Semantic Scholar API by DOI.
    
    Args:
        doi: DOI string
    
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
    
    url = f"{SEMANTIC_SCHOLAR_BASE_URL}/graph/v1/paper/DOI:{quote(doi)}"
    params = {
        "fields": "citationCount,influentialCitationCount,referenceCount,title,authors,year,venue"
    }
    headers = get_s2_headers()
    
    for attempt in range(S2_MAX_RETRIES):
        try:
            response = requests.get(url, headers=headers, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            # Extract useful fields
            enriched = {
                "citation_count": data.get("citationCount", 0),
                "influential_citation_count": data.get("influentialCitationCount", 0),
                "reference_count": data.get("referenceCount", 0),
                "title": data.get("title"),
                "year": data.get("year"),
                "venue": data.get("venue"),
                "authors": data.get("authors", []),
                "raw_s2": data  # Keep full response for reference
            }
            
            return enriched
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.debug(f"Paper not found in Semantic Scholar: {doi}")
                return None
            elif e.response.status_code == 429:
                wait_time = (attempt + 1) * 5  # Longer wait for rate limits
                logger.warning(f"Rate limited. Waiting {wait_time}s...")
                time.sleep(wait_time)
                continue
            logger.warning(f"HTTP error for DOI {doi}: {e.response.status_code}")
            return None
            
        except requests.exceptions.RequestException as e:
            if attempt < S2_MAX_RETRIES - 1:
                time.sleep(2)
                continue
            logger.warning(f"Request failed for DOI {doi}: {e}")
            return None
    
    return None


def enrich_work_by_title(title: str, year: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """
    Enrich work metadata using Semantic Scholar API by title.
    
    Args:
        title: Paper title
        year: Optional publication year
    
    Returns:
        Enriched metadata dictionary or None if failed
    """
    if not title:
        return None
    
    url = f"{SEMANTIC_SCHOLAR_BASE_URL}/graph/v1/paper/search"
    params = {
        "query": title,
        "fields": "citationCount,influentialCitationCount,referenceCount,title,authors,year,venue,paperId",
        "limit": 1
    }
    if year:
        params["year"] = year
    
    headers = get_s2_headers()
    
    for attempt in range(S2_MAX_RETRIES):
        try:
            response = requests.get(url, headers=headers, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            papers = data.get("data", [])
            if not papers:
                return None
            
            paper = papers[0]
            
            # Extract useful fields
            enriched = {
                "citation_count": paper.get("citationCount", 0),
                "influential_citation_count": paper.get("influentialCitationCount", 0),
                "reference_count": paper.get("referenceCount", 0),
                "title": paper.get("title"),
                "year": paper.get("year"),
                "venue": paper.get("venue"),
                "authors": paper.get("authors", []),
                "paper_id": paper.get("paperId"),
                "raw_s2": paper
            }
            
            return enriched
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                wait_time = (attempt + 1) * 5
                logger.warning(f"Rate limited. Waiting {wait_time}s...")
                time.sleep(wait_time)
                continue
            logger.warning(f"HTTP error for title search: {e.response.status_code}")
            return None
            
        except requests.exceptions.RequestException as e:
            if attempt < S2_MAX_RETRIES - 1:
                time.sleep(2)
                continue
            logger.warning(f"Request failed for title search: {e}")
            return None
    
    return None


def enrich_works_batch(
    works: List[Dict[str, Any]],
    max_enrichments: Optional[int] = None,
    use_title_fallback: bool = True
) -> List[Dict[str, Any]]:
    """
    Enrich a batch of works with Semantic Scholar metadata.
    
    Args:
        works: List of work dictionaries
        max_enrichments: Maximum number of works to enrich (None = all)
        use_title_fallback: If True, try title search when DOI is missing
    
    Returns:
        List of enriched work dictionaries
    """
    enriched_works = []
    enriched_count = 0
    
    for work in works:
        if max_enrichments and enriched_count >= max_enrichments:
            enriched_works.append(work)
            continue
        
        enriched_data = None
        
        # Try DOI first
        doi = work.get("doi")
        if doi:
            enriched_data = enrich_work_by_doi(doi)
        
        # Fallback to title search if DOI failed and use_title_fallback is True
        if not enriched_data and use_title_fallback:
            title = work.get("title")
            year = work.get("publication_year")
            if title:
                enriched_data = enrich_work_by_title(title, year=year)
        
        if enriched_data:
            # Merge enrichment data into work
            work["semantic_scholar_enrichment"] = enriched_data
            enriched_count += 1
        
        enriched_works.append(work)
        time.sleep(S2_RATE_LIMIT_DELAY)
    
    logger.info(f"Enriched {enriched_count} works with Semantic Scholar metadata")
    return enriched_works


def save_enriched_works(works: List[Dict[str, Any]], filename: str = "works_s2_enriched.json") -> None:
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
        {"title": "Another test work", "publication_year": 2020}
    ]
    enriched = enrich_works_batch(test_works, max_enrichments=10)
    logger.info(f"Enriched {len(enriched)} works")
