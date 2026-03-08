"""
Database connection and utility functions for PostgreSQL.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from contextlib import contextmanager
from typing import Generator, Tuple
import logging

from scripts.config import DB_CONFIG

logger = logging.getLogger(__name__)


def get_db_connection_string() -> str:
    """Construct PostgreSQL connection string from config."""
    return (
        f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
        f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
    )


def detect_connection_mode(host: str) -> str:
    """Detect Supabase connection mode from host.
    
    Returns:
        "session_pooler" if host contains "pooler.supabase.com"
        "direct" if host starts with "db." and contains ".supabase.co"
        Raises ValueError if host doesn't match known patterns
    """
    host_lower = host.lower()
    if "pooler.supabase.com" in host_lower:
        return "session_pooler"
    elif host_lower.startswith("db.") and ".supabase.co" in host_lower:
        return "direct"
    else:
        raise ValueError(
            f"Unknown Supabase host pattern: {host}. "
            f"Expected either pooler host (pooler.supabase.com) or direct host (db.*.supabase.co)"
        )


def validate_host_user_mode(host: str, user: str):
    """Validate that host and user match the same connection mode.
    
    Raises:
        RuntimeError: If host/user mismatch is detected
    """
    mode = detect_connection_mode(host)
    
    if mode == "session_pooler":
        if not user.startswith("postgres."):
            raise RuntimeError(
                f"Connection mode mismatch: Session pooler host '{host}' requires user "
                f"starting with 'postgres.' (e.g., 'postgres.PROJECT_ID'), but got '{user}'. "
                f"Please use the session pooler connection string from Supabase."
            )
    elif mode == "direct":
        if user != "postgres":
            raise RuntimeError(
                f"Connection mode mismatch: Direct host '{host}' requires user exactly "
                f"'postgres', but got '{user}'. "
                f"Please use the direct connection credentials from Supabase."
            )


def create_db_engine(port_override=None):
    """Create SQLAlchemy engine for database operations.
    
    Args:
        port_override: Optional port to use instead of DB_CONFIG['port']
    
    Raises:
        RuntimeError: If host is localhost or host/user mismatch
        ValueError: If required credentials are missing
    """
    # Get required credentials - will raise ValueError if missing
    host = DB_CONFIG['host']
    port = port_override if port_override is not None else DB_CONFIG['port']
    database = DB_CONFIG['database']
    user = DB_CONFIG['user']
    password = DB_CONFIG['password']
    
    # Production safeguard: raise RuntimeError if host is localhost
    if host == "localhost":
        raise RuntimeError(
            "Database host is 'localhost'. Supabase credentials were not loaded. "
            "Please set POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, "
            "and POSTGRES_PASSWORD in Streamlit secrets or environment variables."
        )
    
    # Detect connection mode and validate host/user match
    try:
        mode = detect_connection_mode(host)
        validate_host_user_mode(host, user)
    except ValueError as e:
        raise RuntimeError(str(e))
    
    # URL encode password to handle special characters
    from urllib.parse import quote_plus
    password_encoded = quote_plus(password)
    
    # Build connection string from the five POSTGRES_* values
    connection_string = (
        f"postgresql://{user}:{password_encoded}"
        f"@{host}:{port}/{database}"
    )
    
    # For Transaction Pooler (port 6543), add pgbouncer parameter
    # Session Pooler on port 5432 doesn't need explicit pgbouncer=true
    if port == 6543 and mode != "session_pooler":
        connection_string += "?pgbouncer=true"
        logger.debug("Added pgbouncer=true parameter")
    
    # Supabase connection settings - always use SSL require
    ssl_mode = "require"
    connect_args = {
        "connect_timeout": 15,
        "sslmode": ssl_mode
    }
    
    # Safe debug log (never log password)
    logger.info("Database connection configuration:")
    logger.info(f"  Host: {host}")
    logger.info(f"  Port: {port}")
    logger.info(f"  User: {user}")
    logger.info(f"  Mode: {mode}")
    logger.info(f"  SSL: {ssl_mode}")
    
    engine = create_engine(
        connection_string,
        poolclass=NullPool,
        echo=False,
        connect_args=connect_args,
        pool_pre_ping=True  # Verify connections before using
    )
    return engine


@contextmanager
def get_db_session() -> Generator:
    """Context manager for database sessions."""
    engine = create_db_engine()
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        session.close()
        engine.dispose()


def execute_sql_file(engine, file_path: str) -> None:
    """Execute SQL commands from a file."""
    with open(file_path, 'r') as f:
        sql_content = f.read()
    
    # Split by semicolons and execute each statement
    statements = [s.strip() for s in sql_content.split(';') if s.strip()]
    
    with engine.connect() as conn:
        for statement in statements:
            if statement:
                try:
                    conn.execute(text(statement))
                    conn.commit()
                except Exception as e:
                    logger.warning(f"SQL execution warning: {e}")
                    conn.rollback()


def test_connection() -> Tuple[bool, str]:
    """Test database connection using only the configured host/port.
    
    Returns:
        Tuple of (success: bool, message: str)
    """
    # Get required credentials - will raise ValueError if missing
    host = DB_CONFIG['host']
    port = DB_CONFIG['port']
    user = DB_CONFIG['user']
    database = DB_CONFIG['database']
    
    # Detect connection mode for logging
    try:
        mode = detect_connection_mode(host)
    except ValueError:
        mode = "unknown"
    
    logger.info(f"Testing connection: {user}@{host}:{port}/{database} (mode: {mode})")
    
    # Use only the configured host/port - no fallbacks
    try:
        engine = create_db_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()  # Actually fetch to ensure connection works
        engine.dispose()
        logger.info(f"Database connection successful")
        return True, f"Connected to {host}:{port} (mode: {mode})"
    except Exception as e:
        error_str = str(e)
        logger.error(f"Connection failed: {error_str}")
        
        # Provide helpful error messages
        error_lower = error_str.lower()
        if "connection mode mismatch" in error_lower:
            message = f"Connection mode mismatch: {error_str}"
        elif "connection refused" in error_lower or "could not connect" in error_lower:
            message = (
                f"Connection refused. Check:\n"
                f"- Host: {host}\n"
                f"- Port: {port}\n"
                f"- Mode: {mode}\n"
                f"- Verify credentials match the connection mode"
            )
        elif "authentication" in error_lower or "password" in error_lower:
            message = (
                f"Authentication failed. Check:\n"
                f"- User: {user}\n"
                f"- Password is correct\n"
                f"- Mode: {mode}"
            )
        elif "could not translate host name" in error_lower:
            message = (
                f"DNS resolution failed. Check:\n"
                f"- Host: {host}\n"
                f"- Network connectivity"
            )
        else:
            message = f"Connection failed: {error_str[:200]}"
        
        logger.error(f"Database connection failed: {message}")
        return False, message
