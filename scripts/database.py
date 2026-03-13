"""
Database connection and utility functions for PostgreSQL.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool, QueuePool
from sqlalchemy.exc import OperationalError
from contextlib import contextmanager
from typing import Generator, Tuple, Optional
import logging
import time

from scripts.config import DB_CONFIG

logger = logging.getLogger(__name__)

# Shared engine instance (singleton pattern)
_shared_engine: Optional[object] = None


def _build_connection_string(host: str, port: int, database: str, user: str, password: str) -> str:
    """Build PostgreSQL connection string with URL-encoded password.
    
    This is the shared function used by both get_db_connection_string() and create_db_engine().
    
    Args:
        host: Database host
        port: Database port
        database: Database name
        user: Database user
        password: Database password (will be URL-encoded)
    
    Returns:
        PostgreSQL connection string with URL-encoded password
    """
    from urllib.parse import quote_plus
    password_encoded = quote_plus(password)
    return f"postgresql://{user}:{password_encoded}@{host}:{port}/{database}"


def get_db_connection_string() -> str:
    """Construct PostgreSQL connection string from config."""
    return _build_connection_string(
        host=DB_CONFIG['host'],
        port=DB_CONFIG['port'],
        database=DB_CONFIG['database'],
        user=DB_CONFIG['user'],
        password=DB_CONFIG['password']
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


def create_db_engine(port_override=None, force_new=False):
    """
    Create or return shared SQLAlchemy engine for database operations.
    
    Uses singleton pattern to ensure only one engine instance exists,
    preventing connection exhaustion in Supabase pooler mode.
    
    Args:
        port_override: Optional port to use instead of DB_CONFIG['port']
        force_new: If True, create a new engine even if one exists (for testing)
    
    Returns:
        SQLAlchemy engine instance
    
    Raises:
        RuntimeError: If host is localhost or host/user mismatch
        ValueError: If required credentials are missing
    """
    global _shared_engine
    
    # Return existing engine unless force_new is True
    if _shared_engine is not None and not force_new:
        return _shared_engine
    
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
    
    # Build connection string using shared function (password is URL-encoded inside)
    connection_string = _build_connection_string(
        host=host,
        port=port,
        database=database,
        user=user,
        password=password
    )
    
    # For Transaction Pooler (port 6543), add pgbouncer parameter
    # Session Pooler on port 5432 doesn't need explicit pgbouncer=true
    if port == 6543 and mode != "session_pooler":
        connection_string += "?pgbouncer=true"
        logger.debug("Added pgbouncer=true parameter")
    
    # Determine pool strategy based on connection mode
    # Session pooler mode: Use NullPool (no connection pooling at SQLAlchemy level)
    # Direct mode: Use QueuePool with conservative settings
    if mode == "session_pooler":
        poolclass = NullPool
        pool_log = "NullPool (session pooler mode)"
        
        # NullPool-specific settings (no pool_size, max_overflow, or pool_timeout)
        engine_kwargs = {
            "pool_pre_ping": True,  # Verify connections before using
            "pool_recycle": 300,    # Recycle connections after 5 minutes
            "connect_args": {
                "connect_timeout": 15,
                "sslmode": "require"
            }
        }
    else:
        poolclass = QueuePool
        pool_log = "QueuePool (direct mode, pool_size=1, max_overflow=0)"
        
        # QueuePool-specific settings (includes pool_size, max_overflow, pool_timeout)
        engine_kwargs = {
            "pool_pre_ping": True,  # Verify connections before using
            "pool_recycle": 300,    # Recycle connections after 5 minutes
            "pool_size": 1,         # Only 1 connection in pool
            "max_overflow": 0,      # No overflow connections
            "pool_timeout": 30,     # Wait up to 30s for connection from pool
            "connect_args": {
                "connect_timeout": 15,
                "sslmode": "require"
            }
        }
    
    engine = create_engine(
        connection_string,
        poolclass=poolclass,
        **engine_kwargs
    )
    
    logger.info(f"Created database engine: {pool_log} for {user}@{host}:{port}/{database}")
    
    # Store as shared engine if not forcing new
    if not force_new:
        _shared_engine = engine
    
    return engine


def dispose_db_engine():
    """Dispose the shared database engine and release all connections."""
    global _shared_engine
    if _shared_engine is not None:
        logger.info("Disposing shared database engine and releasing connections")
        _shared_engine.dispose()
        _shared_engine = None


def get_db_engine_with_retry(max_retries=3, base_delay=2):
    """
    Get database engine with retry logic for connection exhaustion errors.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds for exponential backoff
    
    Returns:
        SQLAlchemy engine instance
    
    Raises:
        OperationalError: If connection fails after all retries
    """
    for attempt in range(max_retries):
        try:
            engine = create_db_engine()
            # Test connection immediately
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return engine
        except OperationalError as e:
            error_str = str(e).lower()
            if "max clients" in error_str or "maxclients" in error_str:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)  # Exponential backoff: 2s, 4s, 8s
                    logger.warning(
                        f"Connection exhaustion detected (attempt {attempt + 1}/{max_retries}). "
                        f"Retrying in {delay}s..."
                    )
                    time.sleep(delay)
                    continue
                else:
                    logger.error(f"Connection exhaustion after {max_retries} retries")
                    raise
            else:
                # Not a connection exhaustion error, re-raise immediately
                raise
    raise OperationalError("Failed to acquire database connection after retries", None, None)


@contextmanager
def get_db_session() -> Generator:
    """Context manager for database sessions using shared engine."""
    engine = create_db_engine()  # Uses shared engine
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
        # Do NOT dispose engine here - it's shared


def execute_sql_file(engine, file_path: str) -> None:
    """Execute SQL commands from a file using provided engine."""
    with open(file_path, 'r') as f:
        sql_content = f.read()
    
    # Split by semicolons and execute each statement
    statements = [s.strip() for s in sql_content.split(';') if s.strip()]
    
    with engine.begin() as conn:  # Use begin() for transaction management
        for statement in statements:
            if statement:
                try:
                    conn.execute(text(statement))
                except Exception as e:
                    logger.warning(f"SQL execution warning: {e}")
                    raise  # Let begin() handle rollback


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
    
    # Hard failure if host is localhost - env vars were not loaded
    if host == "localhost":
        raise RuntimeError(
            "Database host is 'localhost'. Environment variables were not loaded. "
            "Please set POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, "
            "and POSTGRES_PASSWORD in Streamlit secrets or environment variables."
        )
    
    # Detect connection mode for logging
    try:
        mode = detect_connection_mode(host)
    except ValueError:
        mode = "unknown"
    
    logger.info(f"Testing connection: {user}@{host}:{port}/{database} (mode: {mode})")
    
    # Use only the configured host/port - no fallbacks, no alternate ports
    try:
        engine = create_db_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()  # Actually fetch to ensure connection works
        # Do NOT dispose - engine is shared
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
