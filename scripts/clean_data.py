"""
Data cleaning module.
Cleans and standardizes raw data from OpenAlex API.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd

from scripts.config import RAW_DATA_DIR, PROCESSED_DATA_DIR

logger = logging.getLogger(__name__)

# Ensure directories exist
PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)


def clean_institution_data(raw_institutions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Clean and standardize raw institution data from OpenAlex.
    
    Args:
        raw_institutions: List of raw institution dictionaries
    
    Returns:
        List of cleaned institution dictionaries
    """
    logger.info(f"Cleaning {len(raw_institutions)} institution records...")
    
    cleaned = []
    
    for inst in raw_institutions:
        # Extract essential fields
        cleaned_inst = {
            "id": inst.get("id", ""),
            "display_name": inst.get("display_name", "").strip(),
            "country_code": inst.get("country_code", "").upper() if inst.get("country_code") else None,
            "type": inst.get("type", ""),
            "summary_stats": inst.get("summary_stats", {}),
            "ids": inst.get("ids", {}),  # Includes ROR ID
            "counts_by_year": inst.get("counts_by_year", []),
            "geo": inst.get("geo", {}),
            "associated_institutions": inst.get("associated_institutions", []),
            "concepts": inst.get("x_concepts", [])  # OpenAlex uses x_concepts
        }
        
        # Only include if has essential data
        if cleaned_inst["display_name"] and cleaned_inst["id"]:
            cleaned.append(cleaned_inst)
    
    logger.info(f"Cleaned {len(cleaned)} institution records")
    return cleaned


def clean_works_data(raw_works: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Clean and standardize raw works data from OpenAlex.
    
    Args:
        raw_works: List of raw work dictionaries
    
    Returns:
        List of cleaned work dictionaries
    """
    logger.info(f"Cleaning {len(raw_works)} work records...")
    
    cleaned = []
    
    for work in raw_works:
        cleaned_work = {
            "id": work.get("id", ""),
            "title": work.get("title", ""),
            "publication_year": work.get("publication_year"),
            "cited_by_count": work.get("cited_by_count", 0),
            "authorships": work.get("authorships", []),
            "concepts": work.get("x_concepts", []),  # Subject classifications
            "primary_location": work.get("primary_location", {}),
            "open_access": work.get("open_access", {}),
            "type": work.get("type", "")
        }
        
        if cleaned_work["id"]:
            cleaned.append(cleaned_work)
    
    logger.info(f"Cleaned {len(cleaned)} work records")
    return cleaned


def save_cleaned_data(data: List[Dict[str, Any]], filename: str) -> None:
    """Save cleaned data to JSON file."""
    filepath = PROCESSED_DATA_DIR / filename
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved {len(data)} cleaned records to {filepath}")


def load_cleaned_data(filename: str) -> List[Dict[str, Any]]:
    """Load cleaned data from JSON file."""
    filepath = PROCESSED_DATA_DIR / filename
    if not filepath.exists():
        logger.warning(f"Cleaned data file not found: {filepath}")
        return []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    from scripts.extract_data import load_raw_data
    
    # Clean institutions
    raw_institutions = load_raw_data("institutions_raw.json")
    if raw_institutions:
        cleaned_institutions = clean_institution_data(raw_institutions)
        save_cleaned_data(cleaned_institutions, "institutions_cleaned.json")
    
    # Clean works (if available)
    raw_works_list = load_raw_data("institution_works_raw.json")
    if raw_works_list:
        # Flatten works data
        all_works = []
        for item in raw_works_list:
            works = item.get("works", [])
            all_works.extend(works)
        
        if all_works:
            cleaned_works = clean_works_data(all_works)
            save_cleaned_data(cleaned_works, "works_cleaned.json")
