import logging
import os
from contextlib import contextmanager
from typing import Generator, Optional
from dotenv import load_dotenv
import psycopg2
from psycopg2.extensions import connection, cursor
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

# Load environment variables from .env files
_env_dirs = [
    os.path.join(os.path.dirname(__file__), ".."),
    os.path.join(os.path.dirname(__file__), "..", ".."),
    os.getcwd(),
    os.path.join(os.getcwd(), "backend"),
]
for _d in _env_dirs:
    _p = os.path.join(_d, ".env")
    if os.path.exists(_p):
        load_dotenv(_p, override=True)

# Configuration loaded from environment with sensible defaults
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "hospital_db")
POSTGRES_USER = os.getenv("POSTGRES_USER", os.getenv("USER", "postgres"))
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")
DATABASE_URL = os.getenv("DATABASE_URL")
# Short connection timeout in seconds to ensure the API never hangs when PostgreSQL is offline
CONNECT_TIMEOUT = int(os.getenv("POSTGRES_CONNECT_TIMEOUT", "2"))


def get_db_connection() -> Optional[connection]:
    """
    Attempt to establish a connection to PostgreSQL.
    Returns connection instance if successful, None if unable to connect.
    Handles all connection errors gracefully using try...except.
    """
    try:
        if DATABASE_URL:
            conn = psycopg2.connect(DATABASE_URL, connect_timeout=CONNECT_TIMEOUT)
        else:
            conn = psycopg2.connect(
                host=POSTGRES_HOST,
                port=POSTGRES_PORT,
                dbname=POSTGRES_DB,
                user=POSTGRES_USER,
                password=POSTGRES_PASSWORD,
                connect_timeout=CONNECT_TIMEOUT,
            )
        return conn
    except Exception as e:
        logger.warning(f"[Database] Could not connect to PostgreSQL ({POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}): {e}")
        return None


@contextmanager
def get_cursor(commit: bool = False) -> Generator[Optional[cursor], None, None]:
    """
    Context manager yielding a RealDictCursor.
    Automatically handles commit/rollback and connection closing.
    If database is offline, yields None without raising exceptions.
    """
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        if conn is None:
            yield None
            return

        cur = conn.cursor(cursor_factory=RealDictCursor)
        yield cur
        if commit:
            conn.commit()
    except Exception as e:
        logger.warning(f"[Database] Query execution error: {e}")
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        yield None
    finally:
        if cur:
            try:
                cur.close()
            except Exception:
                pass
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def check_connection() -> bool:
    """
    Quick boolean probe to verify if PostgreSQL is actively reachable.
    """
    try:
        conn = get_db_connection()
        if conn is not None:
            conn.close()
            return True
        return False
    except Exception:
        return False
