"""
Entity resolution module for standardizing institution names.
Implements fuzzy matching, canonical name mapping, and ROR API integration.
"""

import json
import logging
import requests
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from rapidfuzz import fuzz, process
import pycountry
import time

from scripts.config import RAW_DATA_DIR, PROCESSED_DATA_DIR

# ROR API base URL
ROR_API_BASE = "https://api.ror.org"

logger = logging.getLogger(__name__)

# Ensure processed data directory exists
PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)


# Common institution name variations and canonical mappings
CANONICAL_MAPPINGS = {
    # US Institutions
    "Massachusetts Institute of Technology": ["MIT", "Massachusetts Institute of Technology", "MIT Cambridge"],
    "Harvard University": ["Harvard", "Harvard University", "Harvard College"],
    "Stanford University": ["Stanford", "Stanford University"],
    "University of California, Berkeley": ["UC Berkeley", "UCB", "University of California Berkeley", "Berkeley"],
    "California Institute of Technology": ["Caltech", "Cal Tech", "California Institute of Technology"],
    "Princeton University": ["Princeton", "Princeton University"],
    "Yale University": ["Yale", "Yale University"],
    "University of Chicago": ["UChicago", "University of Chicago", "Chicago"],
    "Columbia University": ["Columbia", "Columbia University"],
    "University of Pennsylvania": ["UPenn", "University of Pennsylvania", "Penn"],
    
    # UK Institutions
    "University of Oxford": ["Oxford", "Oxford University", "University of Oxford"],
    "University of Cambridge": ["Cambridge", "Cambridge University", "University of Cambridge"],
    "Imperial College London": ["Imperial", "Imperial College", "Imperial College London"],
    "University College London": ["UCL", "University College London"],
    
    # Canadian Institutions
    "University of Toronto": ["UofT", "University of Toronto", "Toronto"],
    "University of British Columbia": ["UBC", "University of British Columbia"],
    "McGill University": ["McGill", "McGill University"],
    "University of Alberta": ["UAlberta", "University of Alberta", "U of A"],
    
    # Other International
    "ETH Zurich": ["ETH", "ETH Zurich", "Swiss Federal Institute of Technology"],
    "National University of Singapore": ["NUS", "National University of Singapore"],
    "Tsinghua University": ["Tsinghua", "Tsinghua University"],
    "Peking University": ["Peking", "Peking University", "Beijing University"],
}


def normalize_country_name(country_code: Optional[str], country_name: Optional[str]) -> Optional[str]:
    """Normalize country name using pycountry."""
    if country_code:
        try:
            country = pycountry.countries.get(alpha_2=country_code)
            if country:
                return country.name
        except:
            pass
    
    if country_name:
        try:
            # Try to find by name
            country = pycountry.countries.search_fuzzy(country_name)[0]
            return country.name
        except:
            return country_name
    
    return None


def extract_institution_name_variations(display_name: str, alternate_names: List[str]) -> List[str]:
    """Extract all name variations for an institution."""
    variations = [display_name]
    if alternate_names:
        variations.extend(alternate_names)
    return variations


def search_ror_api(query: str) -> Optional[Dict[str, Any]]:
    """
    Search ROR API for institution metadata.
    
    Args:
        query: Institution name or identifier to search
    
    Returns:
        ROR record if found, None otherwise
    """
    url = f"{ROR_API_BASE}/organizations"
    params = {"query": query}
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        items = data.get("items", [])
        if items:
            return items[0]  # Return first match
    except requests.exceptions.RequestException as e:
        logger.debug(f"ROR API search failed for '{query}': {e}")
    
    return None


def get_ror_metadata(ror_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch ROR metadata by ROR ID.
    
    Args:
        ror_id: ROR identifier (e.g., "03yrm5c26")
    
    Returns:
        ROR record if found
    """
    url = f"{ROR_API_BASE}/organizations/{ror_id}"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.debug(f"ROR API fetch failed for '{ror_id}': {e}")
    
    return None


def find_canonical_name(
    institution_name: str,
    ror_id: Optional[str] = None,
    threshold: int = 85
) -> Tuple[Optional[str], Optional[str], str, float]:
    """
    Find canonical name for an institution using ROR API and fuzzy matching.
    
    Args:
        institution_name: The institution name to resolve
        ror_id: Optional ROR ID from OpenAlex data
        threshold: Minimum similarity score (0-100) for fuzzy matching
    
    Returns:
        Tuple of (canonical_name, ror_id, match_method, confidence)
        match_method: 'exact_ror', 'ror_search', 'exact_mapping', 'fuzzy_mapping', 'none'
        confidence: 0-100 score
    """
    # First, try ROR API if ROR ID is available
    if ror_id:
        ror_data = get_ror_metadata(ror_id)
        if ror_data:
            canonical = ror_data.get("name")
            if canonical:
                logger.debug(f"Found canonical name via ROR ID: {canonical}")
                return canonical, ror_id, "exact_ror", 100.0
    
    # Try ROR search API
    ror_result = search_ror_api(institution_name)
    if ror_result:
        canonical = ror_result.get("name")
        found_ror_id = ror_result.get("id", "").split("/")[-1]
        if canonical:
            # Calculate confidence based on name similarity
            similarity = fuzz.ratio(institution_name.lower(), canonical.lower())
            logger.debug(f"Found canonical name via ROR search: {canonical} (confidence: {similarity})")
            return canonical, found_ror_id, "ror_search", float(similarity)
    
    # Check exact matches in canonical mappings
    for canonical, variations in CANONICAL_MAPPINGS.items():
        if institution_name.lower() in [v.lower() for v in variations]:
            return canonical, ror_id, "exact_mapping", 100.0
    
    # Try fuzzy matching against known mappings
    best_match = process.extractOne(
        institution_name,
        CANONICAL_MAPPINGS.keys(),
        scorer=fuzz.token_sort_ratio,
        score_cutoff=threshold
    )
    
    if best_match:
        canonical, score, _ = best_match
        return canonical, ror_id, "fuzzy_mapping", float(score)
    
    # If no match found, use the original name as canonical
    return institution_name, ror_id, "none", 0.0


def resolve_institution_entities(raw_institutions: List[Dict]) -> List[Dict]:
    """
    Resolve and standardize institution entities using ROR API and fuzzy matching.
    
    Args:
        raw_institutions: List of raw institution dictionaries from OpenAlex API
    
    Returns:
        List of resolved institution dictionaries with canonical names and ROR IDs
    """
    logger.info(f"Resolving entities for {len(raw_institutions)} institutions...")
    logger.info("Using ROR API for entity resolution...")
    
    resolved = []
    name_to_canonical = {}
    
    for i, inst in enumerate(raw_institutions):
        display_name = inst.get("display_name", "")
        openalex_id = inst.get("id", "").split("/")[-1]
        
        # Extract ROR ID from OpenAlex data if available
        ror_id = None
        ids = inst.get("ids", {})
        if isinstance(ids, dict):
            ror_url = ids.get("ror")
            if ror_url:
                ror_id = ror_url.split("/")[-1]
        
        # Extract country information
        country_code = inst.get("country_code")
        country_name = normalize_country_name(country_code, inst.get("country"))
        
        # Find canonical name using ROR API and fuzzy matching
        canonical_name, resolved_ror_id, match_method, confidence = find_canonical_name(
            display_name, ror_id=ror_id
        )
        
        # Use resolved ROR ID if found
        final_ror_id = resolved_ror_id or ror_id
        
        # Store mapping
        name_to_canonical[display_name] = canonical_name
        
        resolved_inst = {
            "institution_id": None,  # Will be set when loading to DB
            "institution_name": display_name,
            "canonical_name": canonical_name,
            "country": country_name,
            "region": None,  # Could be enhanced with region mapping
            "institution_type": inst.get("type"),
            "openalex_id": openalex_id,
            "ror_id": final_ror_id,
            "match_method": match_method,
            "match_confidence": confidence,
            "raw_data": inst  # Keep raw data for reference
        }
        
        resolved.append(resolved_inst)
        
        # Rate limiting for ROR API
        if (i + 1) % 10 == 0:
            time.sleep(0.5)
    
    # Save mapping for reference
    mapping_file = PROCESSED_DATA_DIR / "institution_name_mapping.json"
    with open(mapping_file, 'w', encoding='utf-8') as f:
        json.dump(name_to_canonical, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Resolved {len(resolved)} institutions")
    logger.info(f"Found {len(set(name_to_canonical.values()))} unique canonical names")
    ror_count = sum(1 for r in resolved if r.get("ror_id"))
    logger.info(f"Resolved {ror_count} institutions with ROR IDs")
    
    return resolved


def load_resolved_entities() -> List[Dict]:
    """Load previously resolved entities."""
    filepath = PROCESSED_DATA_DIR / "institutions_resolved.json"
    if not filepath.exists():
        logger.warning(f"Resolved entities file not found: {filepath}")
        return []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_resolved_entities(resolved_institutions: List[Dict]) -> None:
    """Save resolved entities to JSON file."""
    filepath = PROCESSED_DATA_DIR / "institutions_resolved.json"
    
    # Remove raw_data before saving to reduce file size
    cleaned = []
    for inst in resolved_institutions:
        cleaned_inst = {k: v for k, v in inst.items() if k != "raw_data"}
        cleaned.append(cleaned_inst)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(cleaned, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Saved {len(cleaned)} resolved institutions to {filepath}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Load raw institutions
    from scripts.extract_data import load_raw_data
    raw_institutions = load_raw_data("institutions_raw.json")
    
    if raw_institutions:
        resolved = resolve_institution_entities(raw_institutions)
        save_resolved_entities(resolved)
    else:
        logger.error("No raw institutions found. Run extract_data.py first.")
