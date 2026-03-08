"""
Configuration module for Academic Rankings Analytics Platform.
Handles environment variables, database connections, and project settings.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Any

# Load environment variables from .env file (for local development)
load_dotenv()

# Streamlit Cloud loads secrets into os.environ automatically
# No need for dotenv in Streamlit Cloud, but it's safe to call it

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

# Database configuration
# Streamlit Cloud loads secrets into st.secrets, not environment variables
# We need to access st.secrets lazily (when called, not at import time)
def get_db_config() -> Dict[str, Any]:
    """Get database configuration from Streamlit secrets or environment variables.
    
    This function is called lazily to ensure Streamlit is initialized.
    """
    # Try Streamlit secrets first (for Streamlit Cloud)
    # Streamlit secrets can be accessed as attributes: st.secrets.POSTGRES_HOST
    try:
        import streamlit as st
        if hasattr(st, 'secrets'):
            secrets = st.secrets
            # Try attribute access (Streamlit secrets are accessed as attributes)
            try:
                host = getattr(secrets, "POSTGRES_HOST", None) or ""
                port = getattr(secrets, "POSTGRES_PORT", None) or "5432"
                database = getattr(secrets, "POSTGRES_DB", None) or ""
                user = getattr(secrets, "POSTGRES_USER", None) or ""
                password = getattr(secrets, "POSTGRES_PASSWORD", None) or ""
                
                # If we got any non-empty values from secrets, use them
                if host or database or user or password:
                    return {
                        "host": str(host).strip('"') if host else "",
                        "port": int(str(port).strip('"\'')) if port else 5432,
                        "database": str(database).strip('"') if database else "",
                        "user": str(user).strip('"') if user else "",
                        "password": str(password).strip('"') if password else "",
                    }
            except (AttributeError, TypeError, RuntimeError):
                # Secrets not available or Streamlit not initialized yet
                pass
    except (ImportError, RuntimeError):
        # Not in Streamlit environment or Streamlit not initialized
        pass
    
    # Fallback to environment variables (for local development or scripts)
    return {
        "host": strip_quotes(os.getenv("POSTGRES_HOST", "localhost")),
        "port": int(os.getenv("POSTGRES_PORT", "5432").strip('"\'')),
        "database": strip_quotes(os.getenv("POSTGRES_DB", "academic_rankings")),
        "user": strip_quotes(os.getenv("POSTGRES_USER", "postgres")),
        "password": strip_quotes(os.getenv("POSTGRES_PASSWORD", "")),
    }

# Lazy loading: DB_CONFIG is a property that calls get_db_config() when accessed
class DBConfigProxy:
    """Proxy object that lazily loads DB config from Streamlit secrets or env vars."""
    _config: Dict[str, Any] = None
    
    def __getitem__(self, key: str) -> Any:
        if self._config is None:
            self._config = get_db_config()
        return self._config[key]
    
    def get(self, key: str, default: Any = None) -> Any:
        if self._config is None:
            self._config = get_db_config()
        return self._config.get(key, default)
    
    def __contains__(self, key: str) -> bool:
        if self._config is None:
            self._config = get_db_config()
        return key in self._config

DB_CONFIG: Dict[str, Any] = DBConfigProxy()

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
