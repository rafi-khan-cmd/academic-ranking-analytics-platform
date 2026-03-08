"""
Configuration module for Academic Rankings Analytics Platform.
Handles environment variables, database connections, and project settings.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Any

# Load environment variables
load_dotenv()

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
EXTERNAL_DATA_DIR = DATA_DIR / "external"

# Database configuration
# Strip quotes from environment variables (Streamlit Cloud may add them)
def strip_quotes(value: str) -> str:
    """Remove surrounding quotes from string if present."""
    if value and len(value) >= 2:
        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
            return value[1:-1]
    return value

DB_CONFIG: Dict[str, Any] = {
    "host": strip_quotes(os.getenv("POSTGRES_HOST", "localhost")),
    "port": int(os.getenv("POSTGRES_PORT", "5432").strip('"\'')),
    "database": strip_quotes(os.getenv("POSTGRES_DB", "academic_rankings")),
    "user": strip_quotes(os.getenv("POSTGRES_USER", "postgres")),
    "password": strip_quotes(os.getenv("POSTGRES_PASSWORD", "")),
}

# OpenAlex API configuration
OPENALEX_EMAIL = os.getenv("OPENALEX_EMAIL", "")
OPENALEX_BASE_URL = "https://api.openalex.org"

# Methodology definitions
METHODOLOGIES = {
    "Balanced Model": {
        "publication_weight": 0.2,
        "citation_weight": 0.2,
        "collaboration_weight": 0.2,
        "quality_weight": 0.2,
        "subject_strength_weight": 0.1,
        "productivity_weight": 0.1,
        "description": "A balanced approach weighing all indicators equally"
    },
    "Research Impact Model": {
        "publication_weight": 0.15,
        "citation_weight": 0.35,
        "collaboration_weight": 0.15,
        "quality_weight": 0.25,
        "subject_strength_weight": 0.05,
        "productivity_weight": 0.05,
        "description": "Emphasizes citation impact and research quality"
    },
    "Publication Volume Model": {
        "publication_weight": 0.4,
        "citation_weight": 0.15,
        "collaboration_weight": 0.15,
        "quality_weight": 0.15,
        "subject_strength_weight": 0.1,
        "productivity_weight": 0.05,
        "description": "Prioritizes total publication output"
    },
    "Collaboration-Forward Model": {
        "publication_weight": 0.15,
        "citation_weight": 0.15,
        "collaboration_weight": 0.4,
        "quality_weight": 0.15,
        "subject_strength_weight": 0.1,
        "productivity_weight": 0.05,
        "description": "Emphasizes international collaboration"
    },
    "Subject Excellence Model": {
        "publication_weight": 0.15,
        "citation_weight": 0.2,
        "collaboration_weight": 0.15,
        "quality_weight": 0.2,
        "subject_strength_weight": 0.25,
        "productivity_weight": 0.05,
        "description": "Prioritizes subject-specific excellence"
    }
}

# Subject groups for categorization
SUBJECT_GROUPS = {
    "Natural Sciences": ["Physics", "Chemistry", "Biology", "Mathematics", "Earth Sciences"],
    "Engineering": ["Computer Science", "Electrical Engineering", "Mechanical Engineering", "Civil Engineering"],
    "Social Sciences": ["Economics", "Psychology", "Sociology", "Political Science"],
    "Life Sciences": ["Medicine", "Biology", "Biochemistry", "Neuroscience"],
    "Humanities": ["History", "Literature", "Philosophy", "Linguistics"]
}

# Default year for analysis
DEFAULT_YEAR = 2023

# Normalization method
NORMALIZATION_METHOD = "min_max"
