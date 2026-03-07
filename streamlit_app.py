"""
Streamlit app entry point for deployment.
Redirects to main dashboard application.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Import and run main app
from dashboard.app import *
