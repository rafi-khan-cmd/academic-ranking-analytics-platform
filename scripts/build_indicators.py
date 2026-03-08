"""
Indicator engineering module.
Computes ranking-style indicators from raw data.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
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


def compute_collaboration_rate(works: List[Dict]) -> Tuple[float, float]:
    """
    Compute multi-institution and international collaboration rates.
    
    Returns:
        Tuple of (multi_institution_rate, international_collaboration_rate)
    """
    if not works:
        return 0.0, 0.0
    
    multi_inst_works = 0
    international_works = 0
    
    for work in works:
        authorships = work.get("authorships", [])
        if len(authorships) > 1:
            # Collect all institutions and countries
            institutions = set()
            countries = set()
            
            for authorship in authorships:
                insts = authorship.get("institutions", [])
                for inst in insts:
                    inst_id = inst.get("id")
                    if inst_id:
                        institutions.add(inst_id)
                    country = inst.get("country_code")
                    if country:
                        countries.add(country)
            
            # Multi-institution collaboration
            if len(institutions) > 1:
                multi_inst_works += 1
            
            # International collaboration
            if len(countries) > 1:
                international_works += 1
    
    multi_inst_rate = multi_inst_works / len(works) if works else 0.0
    international_rate = international_works / len(works) if works else 0.0
    
    return multi_inst_rate, international_rate


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


def build_institution_indicators(
    institution_data: Dict,
    works_data: Optional[List[Dict]] = None,
    year: Optional[int] = None,
    subject_id: Optional[int] = None
) -> Dict:
    """
    Build all indicators for a single institution, optionally filtered by year and subject.
    
    Args:
        institution_data: Institution metadata
        works_data: List of works/publications for the institution
        year: Optional year filter
        subject_id: Optional subject filter (for subject-level metrics)
    
    Returns:
        Dictionary with all computed indicators
    """
    if not works_data:
        works_data = []
    
    # Filter by year if specified
    if year:
        works_data = [
            w for w in works_data
            if w.get("publication_year") == year
        ]
    
    # Filter by subject if specified (would need topic mapping)
    # This is a placeholder - actual subject filtering would require topic mapping
    
    # Publication metrics
    pub_metrics = compute_publication_metrics(works_data)
    
    # Quality proxy
    quality_proxy = compute_quality_proxy(works_data)
    
    # Collaboration rates
    multi_inst_rate, international_rate = compute_collaboration_rate(works_data)
    
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
    
    # Subject strength (for subject-level metrics)
    subject_strength = 0.0
    if subject_id and works_data:
        # Subject strength is publication count weighted by citations in this subject
        subject_strength = pub_metrics["citation_count"] / max(pub_metrics["publication_count"], 1)
    
    indicators = {
        "institution_id": institution_data.get("institution_id"),
        "canonical_name": institution_data.get("canonical_name"),
        "year": year or DEFAULT_YEAR,
        "subject_id": subject_id,
        "publication_count": pub_metrics["publication_count"],
        "citation_count": pub_metrics["citation_count"],
        "citations_per_paper": pub_metrics["citations_per_paper"],
        "multi_institution_rate": multi_inst_rate,
        "international_collaboration_rate": international_rate,
        "quality_proxy": quality_proxy,
        "productivity_proxy": productivity_proxy,
        "h_index": h_index,
        "top_percentile_citations": top_percentile,
        "subject_strength_basis": subject_strength
    }
    
    return indicators


def build_indicators_from_resolved_entities(
    resolved_institutions: List[Dict],
    works_data_map: Optional[Dict[str, List[Dict]]] = None,
    years: Optional[List[int]] = None,
    subjects: Optional[List[Dict]] = None
) -> List[Dict]:
    """
    Build indicators for all resolved institutions using real works data from OpenAlex.
    Supports year-level and subject-level aggregation.
    
    Args:
        resolved_institutions: List of resolved institution records
        works_data_map: Optional dictionary mapping OpenAlex institution IDs to works lists
        years: Optional list of years to compute metrics for (None = all years)
        subjects: Optional list of subject dictionaries for subject-level metrics
    
    Returns:
        List of indicator dictionaries (institution-year or institution-subject-year)
    """
    logger.info(f"Building indicators for {len(resolved_institutions)} institutions...")
    
    all_indicators = []
    
    # Handle None works_data_map - treat as empty dict
    if works_data_map is None:
        logger.warning("No works data provided; using fallback indicator path")
        logger.info("Indicators will use institution summary stats from OpenAlex (if available)")
        works_data_map = {}
        
        # Try to load from file as fallback
        from scripts.extract_data import load_raw_data
        works_data_list = load_raw_data("institution_works_raw.json")
        if works_data_list:
            works_data_map = {
                item.get("institution_id"): item.get("works", [])
                for item in works_data_list
            }
            logger.info(f"Loaded works data from file for {len(works_data_map)} institutions")
        else:
            logger.info("No works data file found. Building indicators from institution summary stats only.")
    
    # Determine years to process
    if years is None:
        # Extract years from works data if available
        all_years = set()
        if works_data_map:
            for works_list in works_data_map.values():
                for work in works_list:
                    year = work.get("publication_year")
                    if year:
                        all_years.add(year)
        years = sorted(list(all_years)) if all_years else [DEFAULT_YEAR]
    
    logger.info(f"Computing metrics for years: {years}")
    
    # Build institution-year indicators
    for inst in resolved_institutions:
        openalex_id = inst.get("openalex_id")
        # Safely get works data - works_data_map is guaranteed to be a dict (never None)
        works_data = works_data_map.get(openalex_id, [])
        
        # Build indicators for each year
        for year in years:
            indicators = build_institution_indicators(
                inst,
                works_data=works_data,
                year=year,
                subject_id=None
            )
            all_indicators.append(indicators)
        
        # Build subject-level indicators if subjects provided
        if subjects:
            for subject in subjects:
                # Filter works by subject (would need topic mapping)
                # For now, create placeholder subject indicators
                for year in years:
                    indicators = build_institution_indicators(
                        inst,
                        works_data=works_data,  # Would filter by subject here
                        year=year,
                        subject_id=subject.get("subject_id")
                    )
                    all_indicators.append(indicators)
    
    logger.info(f"Built {len(all_indicators)} indicator records")
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
