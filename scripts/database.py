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


def create_db_engine(port_override=None):
    """Create SQLAlchemy engine for database operations.
    
    Args:
        port_override: Optional port to use instead of DB_CONFIG['port']
    
    Raises:
        RuntimeError: If host is localhost (production safeguard)
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
    
    # URL encode password to handle special characters
    from urllib.parse import quote_plus
    password_encoded = quote_plus(password)
    
    # Build connection string from the five POSTGRES_* values
    connection_string = (
        f"postgresql://{user}:{password_encoded}"
        f"@{host}:{port}/{database}"
    )
    
    # Safe debug log: only log host, never password
    logger.info(f"Connecting to database at host: {host}")
    
    # For Session Pooler (pooler.supabase.com), pgbouncer is handled automatically
    # For Transaction Pooler (port 6543), add pgbouncer parameter
    # Note: Session Pooler on port 5432 doesn't need explicit pgbouncer=true
    if port == 6543 and 'pooler.supabase.com' not in host:
        connection_string += "?pgbouncer=true"
        logger.debug("Added pgbouncer=true parameter")
    
    # Supabase connection settings - always use SSL require
    connect_args = {
        "connect_timeout": 15,
        "sslmode": "require"
    }
    
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
    """Test database connection with fallback ports.
    
    Returns:
        Tuple of (success: bool, message: str)
    """
    # Log config for debugging (without password)
    host = DB_CONFIG.get('host', 'NOT SET')
    port = DB_CONFIG.get('port', 'NOT SET')
    user = DB_CONFIG.get('user', 'NOT SET')
    database = DB_CONFIG.get('database', 'NOT SET')
    password_set = bool(DB_CONFIG.get('password', ''))
    
    logger.info(f"Testing connection: {user}@{host}:{port}/{database} (password: {'SET' if password_set else 'NOT SET'})")
    
    ports_to_try = [DB_CONFIG.get('port', 5432)]
    
    # If using 6543 (pooling), also try 5432 (direct) as fallback
    if ports_to_try[0] == 6543:
        ports_to_try.append(5432)
    # If using 5432 (direct), also try 6543 (pooling) as fallback
    elif ports_to_try[0] == 5432:
        ports_to_try.append(6543)
    
    last_error = None
    for port in ports_to_try:
        try:
            engine = create_db_engine(port_override=port)
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.fetchone()  # Actually fetch to ensure connection works
            engine.dispose()
            if port == DB_CONFIG.get('port', 5432):
                logger.info(f"Database connection successful on port {port}")
                return True, f"Connected on port {port}"
            else:
                logger.warning(f"Connected on fallback port {port} (configured port failed)")
                return True, f"Connected on port {port} (fallback)"
        except Exception as e:
            last_error = e
            error_str = str(e)
            logger.error(f"Connection failed on port {port}: {error_str}")
            # Log more details for common errors
            if "could not translate host name" in error_str.lower():
                logger.error(f"DNS resolution failed for host: {host}")
            elif "connection refused" in error_str.lower():
                logger.error(f"Connection refused - check if host {host} and port {port} are correct")
            elif "authentication" in error_str.lower() or "password" in error_str.lower():
                logger.error(f"Authentication failed - check user and password")
            continue
    
    error_msg = str(last_error).lower() if last_error else "Unknown error"
    full_error = str(last_error) if last_error else "No error details available"
    
    if "connection refused" in error_msg or "could not connect" in error_msg or "could not translate host" in error_msg:
        message = (
            f"Connection refused. Check:\n"
            f"- Host: {host}\n"
            f"- Port: {port}\n"
            f"- Use Session Pooler connection string from Supabase"
        )
    elif "authentication" in error_msg or "password" in error_msg:
        message = (
            f"Authentication failed. Check:\n"
            f"- User: {user} (should include project ID for pooler)\n"
            f"- Password is correct\n"
            f"- Full error: {full_error[:150]}"
        )
    else:
        message = f"Connection failed: {full_error[:200]}"
    
    logger.error(f"Database connection failed: {message}")
    return False, message
