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
    """
    # Use override port if provided, otherwise use config
    port = port_override if port_override is not None else DB_CONFIG.get('port', 5432)
    
    # Build connection string with specified port
    connection_string = (
        f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
        f"@{DB_CONFIG['host']}:{port}/{DB_CONFIG['database']}"
    )
    
    # Add pgbouncer parameter for Session Pooler
    # Session Pooler uses pooler.supabase.com hostname or port 6543
    # This is required for IPv4 compatibility with Supabase poolers
    host = DB_CONFIG.get('host', '')
    if 'pooler.supabase.com' in host or port == 6543:
        connection_string += "?pgbouncer=true"
    
    # Supabase connection settings
    # 'prefer' works for both pooling and direct connections
    connect_args = {
        "connect_timeout": 15,
        "sslmode": "prefer"
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
                conn.execute(text("SELECT 1"))
            engine.dispose()
            if port == DB_CONFIG.get('port', 5432):
                logger.info(f"Database connection successful on port {port}")
                return True, f"Connected on port {port}"
            else:
                logger.warning(f"Connected on fallback port {port} (configured port failed)")
                return True, f"Connected on port {port} (fallback)"
        except Exception as e:
            last_error = e
            logger.debug(f"Connection failed on port {port}: {e}")
            continue
    
    error_msg = str(last_error).lower() if last_error else "Unknown error"
    if "connection refused" in error_msg or "could not connect" in error_msg:
        message = (
            f"Connection refused on all ports. "
            f"Enable connection pooling in Supabase (Settings → Database → Connection Pooling) "
            f"or whitelist Streamlit Cloud IPs for direct connection."
        )
    elif "authentication" in error_msg or "password" in error_msg:
        message = "Authentication failed. Check password in secrets."
    else:
        message = f"Connection failed: {str(last_error)[:200]}"
    
    logger.error(f"Database connection failed: {message}")
    return False, message
