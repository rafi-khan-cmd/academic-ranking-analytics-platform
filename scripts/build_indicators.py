"""
Indicator engineering module.
Computes ranking-style indicators from raw data.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd
import numpy as np

from scripts.config import PROCESSED_DATA_DIR, DEFAULT_YEAR

logger = logging.getLogger(__name__)


def compute_publication_metrics(works: List[Dict]) -> Dict[str, float]:
    """Compute publication-related metrics from works data."""
    if not works:
        return {
            "publication_count": 0,
            "citation_count": 0,
            "citations_per_paper": 0.0
        }
    
    publication_count = len(works)
    citation_count = sum(work.get("cited_by_count", 0) for work in works)
    citations_per_paper = citation_count / publication_count if publication_count > 0 else 0.0
    
    return {
        "publication_count": publication_count,
        "citation_count": citation_count,
        "citations_per_paper": citations_per_paper
    }


def compute_quality_proxy(works: List[Dict], percentile: float = 90) -> float:
    """
    Compute quality proxy based on top percentile citations.
    This approximates high-impact research output.
    """
    if not works:
        return 0.0
    
    citations = [work.get("cited_by_count", 0) for work in works]
    if not citations:
        return 0.0
    
    threshold = np.percentile(citations, percentile)
    top_papers = [c for c in citations if c >= threshold]
    
    # Quality proxy: proportion of high-impact papers weighted by their citations
    if len(top_papers) == 0:
        return 0.0
    
    return sum(top_papers) / len(citations) if citations else 0.0


def compute_collaboration_rate(works: List[Dict]) -> float:
    """
    Compute international collaboration rate.
    Approximates based on number of authors from different countries.
    """
    if not works:
        return 0.0
    
    collaborative_works = 0
    for work in works:
        authorships = work.get("authorships", [])
        if len(authorships) > 1:
            # Check if authors are from different countries
            countries = set()
            for authorship in authorships:
                institutions = authorship.get("institutions", [])
                for inst in institutions:
                    country = inst.get("country_code")
                    if country:
                        countries.add(country)
            
            if len(countries) > 1:
                collaborative_works += 1
    
    return collaborative_works / len(works) if works else 0.0


def compute_productivity_proxy(publication_count: int, citation_count: int, 
                               time_period_years: int = 1) -> float:
    """
    Compute productivity proxy: impact per publication over time.
    """
    if publication_count == 0 or time_period_years == 0:
        return 0.0
    
    # Normalize by time period
    publications_per_year = publication_count / time_period_years
    citations_per_year = citation_count / time_period_years
    
    # Productivity: weighted combination of output and impact
    productivity = (publications_per_year * 0.3) + (citations_per_year * 0.7)
    
    return productivity


def compute_h_index(citations: List[int]) -> int:
    """Compute h-index from citation counts."""
    if not citations:
        return 0
    
    sorted_citations = sorted(citations, reverse=True)
    h_index = 0
    for i, citations_count in enumerate(sorted_citations, 1):
        if citations_count >= i:
            h_index = i
        else:
            break
    
    return h_index


def build_institution_indicators(institution_data: Dict, works_data: Optional[List[Dict]] = None) -> Dict:
    """
    Build all indicators for a single institution.
    
    Args:
        institution_data: Institution metadata
        works_data: List of works/publications for the institution
    
    Returns:
        Dictionary with all computed indicators
    """
    if not works_data:
        works_data = []
    
    # Publication metrics
    pub_metrics = compute_publication_metrics(works_data)
    
    # Quality proxy
    quality_proxy = compute_quality_proxy(works_data)
    
    # Collaboration rate
    collaboration_rate = compute_collaboration_rate(works_data)
    
    # Productivity proxy
    productivity_proxy = compute_productivity_proxy(
        pub_metrics["publication_count"],
        pub_metrics["citation_count"]
    )
    
    # H-index
    citations = [work.get("cited_by_count", 0) for work in works_data]
    h_index = compute_h_index(citations)
    
    # Top percentile citations
    if citations:
        top_percentile = np.percentile(citations, 90)
    else:
        top_percentile = 0.0
    
    indicators = {
        "institution_id": institution_data.get("institution_id"),
        "canonical_name": institution_data.get("canonical_name"),
        "year": DEFAULT_YEAR,
        "publication_count": pub_metrics["publication_count"],
        "citation_count": pub_metrics["citation_count"],
        "citations_per_paper": pub_metrics["citations_per_paper"],
        "international_collaboration_rate": collaboration_rate,
        "quality_proxy": quality_proxy,
        "productivity_proxy": productivity_proxy,
        "h_index": h_index,
        "top_percentile_citations": top_percentile
    }
    
    return indicators


def build_indicators_from_resolved_entities(resolved_institutions: List[Dict],
                                           works_data_map: Optional[Dict[str, List[Dict]]] = None) -> List[Dict]:
    """
    Build indicators for all resolved institutions using real works data from OpenAlex.
    
    Args:
        resolved_institutions: List of resolved institution records
        works_data_map: Optional dictionary mapping OpenAlex institution IDs to works lists
    
    Returns:
        List of indicator dictionaries
    """
    logger.info(f"Building indicators for {len(resolved_institutions)} institutions...")
    
    all_indicators = []
    
    # Load works data if available
    if works_data_map is None:
        from scripts.extract_data import load_raw_data
        works_data_list = load_raw_data("institution_works_raw.json")
        if works_data_list:
            works_data_map = {
                item.get("institution_id"): item.get("works", [])
                for item in works_data_list
            }
            logger.info(f"Loaded works data for {len(works_data_map)} institutions")
    
    for inst in resolved_institutions:
        openalex_id = inst.get("openalex_id")
        works_data = works_data_map.get(openalex_id, []) if works_data_map else []
        
        # Build indicators with real works data
        indicators = build_institution_indicators(inst, works_data=works_data)
        all_indicators.append(indicators)
    
    logger.info(f"Built indicators for {len(all_indicators)} institutions")
    return all_indicators


def save_indicators(indicators: List[Dict], filename: str = "indicators_raw.json") -> None:
    """Save indicators to JSON file."""
    filepath = PROCESSED_DATA_DIR / filename
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(indicators, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved {len(indicators)} indicator records to {filepath}")


def load_indicators(filename: str = "indicators_raw.json") -> List[Dict]:
    """Load indicators from JSON file."""
    filepath = PROCESSED_DATA_DIR / filename
    if not filepath.exists():
        logger.warning(f"Indicators file not found: {filepath}")
        return []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    from scripts.resolve_entities import load_resolved_entities
    resolved = load_resolved_entities()
    
    if resolved:
        indicators = build_indicators_from_resolved_entities(resolved)
        save_indicators(indicators)
    else:
        logger.error("No resolved entities found. Run resolve_entities.py first.")
