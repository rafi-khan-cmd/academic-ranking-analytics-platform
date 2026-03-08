"""
Create sample/demo data for testing the platform without API access.
This generates realistic synthetic data for demonstration purposes.

⚠️ NOTE: This is OPTIONAL demo data only. The production pipeline uses
real data from OpenAlex API by default (200+ institutions).

To use real data, run: python scripts/run_pipeline.py
"""

import json
import random
import logging
from pathlib import Path
from typing import List, Dict
import numpy as np

from scripts.config import RAW_DATA_DIR, PROCESSED_DATA_DIR, DEFAULT_YEAR

logger = logging.getLogger(__name__)

# Ensure directories exist
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)

# Sample institutions (mix of real and representative names)
SAMPLE_INSTITUTIONS = [
    {"name": "Massachusetts Institute of Technology", "country": "United States", "type": "university"},
    {"name": "Harvard University", "country": "United States", "type": "university"},
    {"name": "Stanford University", "country": "United States", "type": "university"},
    {"name": "University of Cambridge", "country": "United Kingdom", "type": "university"},
    {"name": "University of Oxford", "country": "United Kingdom", "type": "university"},
    {"name": "ETH Zurich", "country": "Switzerland", "type": "university"},
    {"name": "University of Toronto", "country": "Canada", "type": "university"},
    {"name": "University of Alberta", "country": "Canada", "type": "university"},
    {"name": "National University of Singapore", "country": "Singapore", "type": "university"},
    {"name": "Tsinghua University", "country": "China", "type": "university"},
    {"name": "Peking University", "country": "China", "type": "university"},
    {"name": "University of Tokyo", "country": "Japan", "type": "university"},
    {"name": "University of Melbourne", "country": "Australia", "type": "university"},
    {"name": "University of Sydney", "country": "Australia", "type": "university"},
    {"name": "Imperial College London", "country": "United Kingdom", "type": "university"},
    {"name": "University College London", "country": "United Kingdom", "type": "university"},
    {"name": "California Institute of Technology", "country": "United States", "type": "university"},
    {"name": "Princeton University", "country": "United States", "type": "university"},
    {"name": "Yale University", "country": "United States", "type": "university"},
    {"name": "Columbia University", "country": "United States", "type": "university"},
    {"name": "University of Chicago", "country": "United States", "type": "university"},
    {"name": "University of Pennsylvania", "country": "United States", "type": "university"},
    {"name": "Cornell University", "country": "United States", "type": "university"},
    {"name": "University of Michigan", "country": "United States", "type": "university"},
    {"name": "University of California, Berkeley", "country": "United States", "type": "university"},
    {"name": "University of California, Los Angeles", "country": "United States", "type": "university"},
    {"name": "University of British Columbia", "country": "Canada", "type": "university"},
    {"name": "McGill University", "country": "Canada", "type": "university"},
    {"name": "University of Edinburgh", "country": "United Kingdom", "type": "university"},
    {"name": "King's College London", "country": "United Kingdom", "type": "university"},
    {"name": "Ludwig Maximilian University of Munich", "country": "Germany", "type": "university"},
    {"name": "Heidelberg University", "country": "Germany", "type": "university"},
    {"name": "Sorbonne University", "country": "France", "type": "university"},
    {"name": "University of Paris", "country": "France", "type": "university"},
    {"name": "Seoul National University", "country": "South Korea", "type": "university"},
    {"name": "KAIST", "country": "South Korea", "type": "university"},
    {"name": "Indian Institute of Technology Bombay", "country": "India", "type": "university"},
    {"name": "University of São Paulo", "country": "Brazil", "type": "university"},
    {"name": "University of Buenos Aires", "country": "Argentina", "type": "university"},
    {"name": "University of Cape Town", "country": "South Africa", "type": "university"},
]


def generate_realistic_metrics(institution_name: str, country: str, rank_tier: int) -> Dict:
    """
    Generate realistic metrics based on institution tier.
    Higher tier = better metrics.
    """
    # Base metrics vary by tier
    base_publications = [5000, 3000, 2000, 1000, 500][min(rank_tier, 4)]
    base_citations = [50000, 30000, 15000, 8000, 3000][min(rank_tier, 4)]
    
    # Add randomness
    publication_count = int(base_publications * random.uniform(0.7, 1.3))
    citation_count = int(base_citations * random.uniform(0.7, 1.3))
    citations_per_paper = citation_count / publication_count if publication_count > 0 else 0
    
    # Collaboration rate (higher for top institutions)
    collaboration_rate = random.uniform(0.3 + rank_tier * 0.1, 0.6 + rank_tier * 0.1)
    collaboration_rate = min(collaboration_rate, 0.95)
    
    # Quality proxy (top percentile citations)
    quality_proxy = citations_per_paper * random.uniform(1.2, 2.0)
    
    # Productivity proxy
    productivity_proxy = citations_per_paper * random.uniform(0.8, 1.2)
    
    # H-index approximation
    h_index = int(np.sqrt(publication_count) * random.uniform(0.8, 1.2))
    
    return {
        "publication_count": publication_count,
        "citation_count": citation_count,
        "citations_per_paper": round(citations_per_paper, 2),
        "international_collaboration_rate": round(collaboration_rate, 4),
        "quality_proxy": round(quality_proxy, 2),
        "productivity_proxy": round(productivity_proxy, 2),
        "h_index": h_index,
        "top_percentile_citations": round(citation_count * 0.1, 2)
    }


def create_sample_raw_data() -> List[Dict]:
    """Create sample raw institution data."""
    logger.info("Creating sample raw institution data...")
    
    raw_institutions = []
    
    for i, inst in enumerate(SAMPLE_INSTITUTIONS):
        # Create OpenAlex-like structure
        inst_id = f"I{i+1:06d}"
        raw_inst = {
            "id": f"https://openalex.org/{inst_id}",
            "display_name": inst["name"],
            "country_code": inst["country"][:2].upper() if len(inst["country"]) >= 2 else "US",
            "type": inst["type"],
            "summary_stats": {
                "2yr_mean_citedness": random.uniform(1.0, 5.0),
                "h_index": random.randint(50, 200)
            }
        }
        raw_institutions.append(raw_inst)
    
    # Save to file
    filepath = RAW_DATA_DIR / "institutions_raw.json"
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(raw_institutions, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Created {len(raw_institutions)} sample institutions")
    return raw_institutions


def create_sample_resolved_entities() -> List[Dict]:
    """Create sample resolved entities."""
    logger.info("Creating sample resolved entities...")
    
    resolved = []
    
    for i, inst in enumerate(SAMPLE_INSTITUTIONS):
        resolved_inst = {
            "institution_id": None,  # Will be set when loading to DB
            "institution_name": inst["name"],
            "canonical_name": inst["name"],  # Use name as canonical for sample
            "country": inst["country"],
            "region": None,
            "institution_type": inst["type"],
            "openalex_id": f"I{i+1:06d}"
        }
        resolved.append(resolved_inst)
    
    # Save to file
    filepath = PROCESSED_DATA_DIR / "institutions_resolved.json"
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(resolved, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Created {len(resolved)} resolved entities")
    return resolved


def create_sample_indicators() -> List[Dict]:
    """Create sample indicator data."""
    logger.info("Creating sample indicators...")
    
    indicators = []
    
    for i, inst in enumerate(SAMPLE_INSTITUTIONS):
        # Assign tier based on position (rough ranking)
        tier = i // 8  # 0-4 tiers
        
        metrics = generate_realistic_metrics(inst["name"], inst["country"], tier)
        
        indicator = {
            "institution_id": None,
            "canonical_name": inst["name"],
            "year": DEFAULT_YEAR,
            **metrics
        }
        indicators.append(indicator)
    
    # Save to file
    filepath = PROCESSED_DATA_DIR / "indicators_raw.json"
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(indicators, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Created {len(indicators)} indicator records")
    return indicators


def create_sample_normalized_metrics() -> List[Dict]:
    """Create sample normalized metrics."""
    logger.info("Creating sample normalized metrics...")
    
    # Load indicators
    from scripts.build_indicators import load_indicators
    indicators = load_indicators()
    
    if not indicators:
        logger.warning("No indicators found. Creating from scratch...")
        indicators = create_sample_indicators()
    
    # Normalize
    from scripts.normalize_metrics import normalize_indicators
    normalized = normalize_indicators(indicators)
    
    # Save
    from scripts.normalize_metrics import save_normalized_metrics
    save_normalized_metrics(normalized)
    
    logger.info(f"Created {len(normalized)} normalized metric records")
    return normalized


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("Creating sample data for testing...")
    print("=" * 50)
    
    # Create raw data
    raw_data = create_sample_raw_data()
    
    # Create resolved entities
    resolved = create_sample_resolved_entities()
    
    # Create indicators
    indicators = create_sample_indicators()
    
    # Create normalized metrics
    normalized = create_sample_normalized_metrics()
    
    print("=" * 50)
    print("Sample data creation complete!")
    print(f"- {len(raw_data)} institutions")
    print(f"- {len(resolved)} resolved entities")
    print(f"- {len(indicators)} indicator records")
    print(f"- {len(normalized)} normalized metric records")
    print("\nNext steps:")
    print("1. Run: python scripts/load_to_postgres.py")
    print("2. Run: python scripts/ranking_engine.py")
    print("3. Run: python scripts/advanced_analytics.py")
    print("4. Start dashboard: streamlit run dashboard/app.py")
