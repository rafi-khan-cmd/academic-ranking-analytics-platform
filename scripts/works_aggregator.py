"""
Streaming works aggregator for memory-efficient processing.
Processes works page-by-page and accumulates only essential metrics.
"""

import logging
from typing import Dict, List, Any, Optional
from collections import defaultdict

try:
    import numpy as np
except ImportError:
    np = None

logger = logging.getLogger(__name__)

# Memory safety: Maximum works to process per institution (dev-safe default)
MAX_WORKS_PER_INSTITUTION = 5000


def create_institution_metrics_accumulator(institution_id: str) -> Dict[str, Any]:
    """
    Create a compact accumulator structure for institution metrics.
    
    This structure stores only aggregated statistics, not full work objects.
    """
    return {
        "institution_id": institution_id,
        "publication_count": 0,
        "citation_sum": 0,
        "citation_counts": [],  # List for h-index and percentile calculations
        "year_counts": defaultdict(int),
        "year_citation_sums": defaultdict(int),
        "multi_institution_count": 0,
        "international_collab_count": 0,
        "works_processed": 0,
        "truncated": False  # Flag if hit MAX_WORKS_PER_INSTITUTION
    }


def process_works_page(
    accumulator: Dict[str, Any],
    works_page: List[Dict[str, Any]],
    max_works: Optional[int] = None
) -> None:
    """
    Process a page of works and update the accumulator in place.
    
    This function extracts only essential fields and discards the full work objects
    immediately after processing, keeping memory usage constant.
    
    Args:
        accumulator: The metrics accumulator to update (modified in place)
        works_page: List of work records from OpenAlex API
        max_works: Maximum works to process before truncating (defaults to MAX_WORKS_PER_INSTITUTION)
    """
    if max_works is None:
        max_works = MAX_WORKS_PER_INSTITUTION
    
    for work in works_page:
        # Check if we've hit the cap BEFORE processing this work
        if accumulator["works_processed"] >= max_works:
            # Only mark as truncated if we're stopping due to the cap
            accumulator["truncated"] = True
            break
        
        # Extract ONLY essential fields - discard rest immediately
        publication_year = work.get("publication_year")
        cited_by_count = work.get("cited_by_count", 0)
        authorships = work.get("authorships", [])
        
        # Update basic counts
        accumulator["publication_count"] += 1
        accumulator["citation_sum"] += cited_by_count
        accumulator["citation_counts"].append(cited_by_count)
        accumulator["works_processed"] += 1
        
        # Update year-based metrics (use int keys for consistency)
        if publication_year:
            year_key = int(publication_year)  # Ensure integer key
            accumulator["year_counts"][year_key] += 1
            accumulator["year_citation_sums"][year_key] += cited_by_count
        
        # Check collaboration (only if multiple authorships)
        if len(authorships) > 1:
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
                accumulator["multi_institution_count"] += 1
            
            # International collaboration
            if len(countries) > 1:
                accumulator["international_collab_count"] += 1
        
        # Work object is now discarded - not stored anywhere


def finalize_institution_metrics(accumulator: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert accumulator to final metrics structure compatible with build_indicators.
    
    This computes derived metrics like h-index and quality proxy from accumulated data.
    """
    from scripts.build_indicators import compute_h_index
    
    publication_count = accumulator["publication_count"]
    citation_sum = accumulator["citation_sum"]
    citation_counts = accumulator["citation_counts"]
    
    # Compute citations per paper
    citations_per_paper = citation_sum / publication_count if publication_count > 0 else 0.0
    
    # Compute collaboration rates
    multi_institution_rate = (
        accumulator["multi_institution_count"] / publication_count 
        if publication_count > 0 else 0.0
    )
    international_collaboration_rate = (
        accumulator["international_collab_count"] / publication_count 
        if publication_count > 0 else 0.0
    )
    
    # Compute h-index
    h_index = compute_h_index(citation_counts) if citation_counts else 0
    
    # Compute quality proxy (top percentile citations)
    quality_proxy = 0.0
    top_percentile_citations = 0.0
    if citation_counts:
        if np is not None:
            threshold = np.percentile(citation_counts, 90)
            # Convert NumPy scalar to Python float immediately
            threshold = float(threshold) if hasattr(threshold, 'item') else float(threshold)
            top_papers = [c for c in citation_counts if c >= threshold]
            if top_papers:
                quality_proxy = float(sum(top_papers) / len(citation_counts))
            top_percentile_citations = threshold
        else:
            # Fallback without numpy
            sorted_citations = sorted(citation_counts, reverse=True)
            percentile_idx = int(len(sorted_citations) * 0.1)  # Top 10%
            if percentile_idx > 0:
                threshold = sorted_citations[percentile_idx - 1]
                top_papers = [c for c in citation_counts if c >= threshold]
                if top_papers:
                    quality_proxy = float(sum(top_papers) / len(citation_counts))
                top_percentile_citations = float(threshold)
    
    # Convert defaultdicts to regular dicts for JSON serialization
    # Ensure year keys are integers (not strings)
    year_counts = {int(k): int(v) for k, v in accumulator["year_counts"].items()}
    year_citation_sums = {int(k): float(v) for k, v in accumulator["year_citation_sums"].items()}
    
    # Validate truncation flag: only True if works_processed >= MAX_WORKS_PER_INSTITUTION
    works_processed = accumulator["works_processed"]
    is_truncated = accumulator.get("truncated", False)
    
    # Recompute truncation flag based on actual count to prevent false positives
    # Only mark as truncated if we actually hit the cap
    validated_truncated = is_truncated and works_processed >= MAX_WORKS_PER_INSTITUTION
    
    return {
        "institution_id": accumulator["institution_id"],
        "publication_count": publication_count,
        "citation_count": citation_sum,
        "citations_per_paper": citations_per_paper,
        "multi_institution_rate": multi_institution_rate,
        "international_collaboration_rate": international_collaboration_rate,
        "quality_proxy": quality_proxy,
        "h_index": h_index,
        "top_percentile_citations": top_percentile_citations,
        "year_counts": year_counts,  # Keys are now integers
        "year_citation_sums": year_citation_sums,  # Keys are now integers
        "works_processed": works_processed,
        "truncated": validated_truncated  # Validated flag
    }
