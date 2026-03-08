#!/usr/bin/env python3
"""
Check database connection mode script.

This script loads database configuration and prints the effective connection mode:
- "direct" for direct Supabase connections
- "session_pooler" for session pooler connections
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.config import DB_CONFIG, is_pooler_host, is_pooler_user


def check_connection_mode():
    """Check and print the effective connection mode."""
    try:
        host = DB_CONFIG.get('host', 'NOT SET')
        user = DB_CONFIG.get('user', 'NOT SET')
        port = DB_CONFIG.get('port', 'NOT SET')
        
        # Determine connection mode
        is_pooler_host_val = is_pooler_host(host)
        is_pooler_user_val = is_pooler_user(user)
        
        if is_pooler_host_val and is_pooler_user_val:
            mode = "session_pooler"
        elif not is_pooler_host_val and not is_pooler_user_val:
            mode = "direct"
        else:
            mode = "MIXED (ERROR)"
        
        print("Database Connection Mode Check")
        print("=" * 50)
        print(f"Mode: {mode}")
        print(f"Host: {host}")
        print(f"User: {user}")
        print(f"Port: {port}")
        print()
        
        if mode == "MIXED (ERROR)":
            print("❌ ERROR: Connection mode mismatch detected!")
            if is_pooler_host_val and not is_pooler_user_val:
                print("   Pooler host requires pooler-style user (e.g., 'postgres.PROJECT_ID')")
            elif not is_pooler_host_val and is_pooler_user_val:
                print("   Direct host requires direct-style user ('postgres')")
            return False
        elif mode == "session_pooler":
            print("✅ Using session pooler connection")
            print("   This is the recommended mode for Streamlit Cloud")
        elif mode == "direct":
            print("✅ Using direct connection")
            print("   Note: Direct connection may require IP whitelisting")
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking connection mode: {e}")
        return False


if __name__ == "__main__":
    success = check_connection_mode()
    sys.exit(0 if success else 1)
