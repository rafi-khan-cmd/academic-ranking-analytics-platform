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
def is_pooler_host(host: str) -> bool:
    """Check if host is a Supabase pooler host."""
    return "pooler.supabase.com" in host.lower()


def is_pooler_user(user: str) -> bool:
    """Check if user is a Supabase pooler user (contains project ID)."""
    return "." in user and user != "postgres"


def _validate_connection_mode(host: str, user: str):
    """Validate that host and user match the same connection mode.
    
    Raises:
        ValueError: If direct host is used with pooler user or vice versa.
    """
    is_pooler_host_val = is_pooler_host(host)
    is_pooler_user_val = is_pooler_user(user)
    
    if is_pooler_host_val and not is_pooler_user_val:
        raise ValueError(
            f"Connection mode mismatch: Pooler host '{host}' requires pooler-style user "
            f"(e.g., 'postgres.PROJECT_ID'), but got direct-style user '{user}'. "
            f"Please use the session pooler connection string from Supabase."
        )
    
    if not is_pooler_host_val and is_pooler_user_val:
        raise ValueError(
            f"Connection mode mismatch: Direct host '{host}' requires direct-style user "
            f"('postgres'), but got pooler-style user '{user}'. "
            f"Please use either direct connection credentials or session pooler credentials."
        )


def get_db_config() -> Dict[str, Any]:
    """Get database configuration from Streamlit secrets or environment variables.
    
    This function is called lazily to ensure Streamlit is initialized.
    Raises ValueError if any required credential is missing or if connection mode is mixed.
    """
    config = {}
    
    # Try Streamlit secrets first (for Streamlit Cloud)
    # Streamlit secrets can be accessed as attributes: st.secrets.POSTGRES_HOST
    try:
        import streamlit as st
        if hasattr(st, 'secrets'):
            secrets = st.secrets
            # Try attribute access (Streamlit secrets are accessed as attributes)
            try:
                # Get all required values - only use secrets if ALL are present
                host = getattr(secrets, "POSTGRES_HOST", None)
                port = getattr(secrets, "POSTGRES_PORT", None)
                database = getattr(secrets, "POSTGRES_DB", None)
                user = getattr(secrets, "POSTGRES_USER", None)
                password = getattr(secrets, "POSTGRES_PASSWORD", None)
                
                # Only use secrets if ALL required values are present
                if all([host, port, database, user, password]):
                    config = {
                        "host": strip_quotes(str(host)),
                        "port": int(strip_quotes(str(port)).strip('\'')),
                        "database": strip_quotes(str(database)),
                        "user": strip_quotes(str(user)),
                        "password": strip_quotes(str(password)),
                    }
                    # Validate connection mode consistency
                    _validate_connection_mode(config["host"], config["user"])
                    return config
            except (AttributeError, TypeError, RuntimeError):
                # Secrets not available or Streamlit not initialized yet
                pass
    except (ImportError, RuntimeError):
        # Not in Streamlit environment or Streamlit not initialized
        pass
    
    # Fallback to environment variables (for local development or scripts)
    # Only use the 5 required keys: POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD
    config = {
        "host": strip_quotes(os.getenv("POSTGRES_HOST", "")),
        "port": os.getenv("POSTGRES_PORT", ""),
        "database": strip_quotes(os.getenv("POSTGRES_DB", "")),
        "user": strip_quotes(os.getenv("POSTGRES_USER", "")),
        "password": strip_quotes(os.getenv("POSTGRES_PASSWORD", "")),
    }
    
    # Validate required credentials - raise ValueError if any are missing
    required_keys = ["host", "port", "database", "user", "password"]
    missing_keys = [key for key in required_keys if not config.get(key)]
    
    if missing_keys:
        missing_vars = ", ".join(f"POSTGRES_{key.upper()}" for key in missing_keys)
        raise ValueError(
            f"Missing required database credentials: {', '.join(missing_keys)}. "
            f"Please set {missing_vars} in Streamlit secrets or environment variables."
        )
    
    # Convert port to int
    try:
        config["port"] = int(str(config["port"]).strip('"\''))
    except (ValueError, AttributeError):
        raise ValueError(f"Invalid POSTGRES_PORT value: {config['port']}. Must be a valid integer.")
    
    # Validate connection mode consistency
    _validate_connection_mode(config["host"], config["user"])
    
    return config

# Lazy loading: DB_CONFIG is a property that calls get_db_config() when accessed
class DBConfigProxy:
    """Proxy object that lazily loads DB config from Streamlit secrets or env vars."""
    _config: Dict[str, Any] = None
    
    def _load_config(self):
        """Load config and log startup debug info."""
        if self._config is None:
            self._config = get_db_config()
            
            # Production safeguard: raise RuntimeError if host is localhost
            if self._config.get("host") == "localhost":
                raise RuntimeError(
                    "Database host is 'localhost'. Supabase credentials were not loaded. "
                    "Please set POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, "
                    "and POSTGRES_PASSWORD in Streamlit secrets or environment variables."
                )
            
            # Startup debug log (only safe values, never password)
            import logging
            logger = logging.getLogger(__name__)
            logger.info("Database configuration loaded:")
            logger.info(f"  Host: {self._config.get('host')}")
            logger.info(f"  User: {self._config.get('user')}")
            logger.info(f"  Port: {self._config.get('port')}")
            logger.info(f"  SSL: enabled (required)")
    
    def __getitem__(self, key: str) -> Any:
        self._load_config()
        return self._config[key]
    
    def get(self, key: str, default: Any = None) -> Any:
        self._load_config()
        return self._config.get(key, default)
    
    def __contains__(self, key: str) -> bool:
        self._load_config()
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
