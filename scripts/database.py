"""
Database connection and utility functions for PostgreSQL.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from contextlib import contextmanager
from typing import Generator
import logging

from scripts.config import DB_CONFIG

logger = logging.getLogger(__name__)


def get_db_connection_string() -> str:
    """Construct PostgreSQL connection string from config."""
    return (
        f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
        f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
    )


def create_db_engine():
    """Create SQLAlchemy engine for database operations."""
    connection_string = get_db_connection_string()
    # Supabase requires SSL connections
    # For connection pooling (port 6543), use 'prefer' SSL mode
    # For direct connection (port 5432), use 'require' SSL mode
    port = DB_CONFIG.get('port', 5432)
    ssl_mode = "prefer" if port == 6543 else "require"
    
    connect_args = {
        "connect_timeout": 10,
        "sslmode": ssl_mode
    }
    engine = create_engine(
        connection_string,
        poolclass=NullPool,
        echo=False,
        connect_args=connect_args
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


def test_connection() -> bool:
    """Test database connection."""
    try:
        engine = create_db_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        logger.info("Database connection successful")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False
