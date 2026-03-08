#!/usr/bin/env python3
"""
Test database connection script.

This script loads database configuration, creates a SQLAlchemy engine,
runs a simple SELECT 1 query, and prints a success or error message.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.database import create_db_engine
from scripts.config import DB_CONFIG
from sqlalchemy import text
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_connection():
    """Test database connection and print result."""
    try:
        # Get config values for error messages (without password)
        host = DB_CONFIG.get('host', 'NOT SET')
        port = DB_CONFIG.get('port', 'NOT SET')
        database = DB_CONFIG.get('database', 'NOT SET')
        user = DB_CONFIG.get('user', 'NOT SET')
        
        logger.info(f"Testing connection to: {user}@{host}:{port}/{database}")
        
        # Create engine
        engine = create_db_engine()
        
        # Test connection with SELECT 1
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
        
        # Success
        print("✅ Database connection successful!")
        print(f"   Host: {host}")
        print(f"   Port: {port}")
        print(f"   Database: {database}")
        print(f"   User: {user}")
        return True
        
    except RuntimeError as e:
        # Production safeguard triggered
        print("❌ Connection failed: Supabase credentials not loaded")
        print(f"   Error: {str(e)}")
        print("\n   Please set the following in Streamlit secrets or environment variables:")
        print("   - POSTGRES_HOST")
        print("   - POSTGRES_PORT")
        print("   - POSTGRES_DB")
        print("   - POSTGRES_USER")
        print("   - POSTGRES_PASSWORD")
        return False
        
    except ValueError as e:
        # Missing required credentials
        print("❌ Connection failed: Missing required database credentials")
        print(f"   Error: {str(e)}")
        print("\n   Please set all required credentials in Streamlit secrets or environment variables:")
        print("   - POSTGRES_HOST")
        print("   - POSTGRES_PORT")
        print("   - POSTGRES_DB")
        print("   - POSTGRES_USER")
        print("   - POSTGRES_PASSWORD")
        return False
        
    except Exception as e:
        # Other connection errors
        error_str = str(e)
        host = DB_CONFIG.get('host', 'NOT SET')
        
        print("❌ Connection failed")
        print(f"   Host: {host}")
        print(f"   Error: {error_str[:200]}")
        
        # Provide helpful error messages
        if "connection refused" in error_str.lower():
            print("\n   Possible issues:")
            print("   - Host or port is incorrect")
            print("   - Database server is not accessible")
            print("   - Firewall blocking connection")
        elif "authentication" in error_str.lower() or "password" in error_str.lower():
            print("\n   Possible issues:")
            print("   - Username or password is incorrect")
            print("   - User does not have permission to access the database")
        elif "could not translate host name" in error_str.lower():
            print("\n   Possible issues:")
            print("   - Hostname is incorrect or DNS resolution failed")
            print("   - Network connectivity issues")
        else:
            print("\n   Check your database credentials and network connectivity.")
        
        return False


if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
