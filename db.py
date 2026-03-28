"""
Database connection and query helper for AlloyDB.

Uses psycopg2 with connection pooling. All credentials are sourced
from environment variables to support Cloud Run deployment.
"""

import os
import json
import logging
from contextlib import contextmanager

import psycopg2
from psycopg2 import pool, extras

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Connection Pool (lazy-initialized)
# ---------------------------------------------------------------------------

_connection_pool: pool.SimpleConnectionPool | None = None


def _get_pool() -> pool.SimpleConnectionPool:
    """Return the connection pool, creating it on first call."""
    global _connection_pool
    if _connection_pool is None or _connection_pool.closed:
        _connection_pool = pool.SimpleConnectionPool(
            minconn=1,
            maxconn=5,
            host=os.environ["DB_HOST"],
            port=os.environ.get("DB_PORT", "5432"),
            dbname=os.environ.get("DB_NAME", "postgres"),
            user=os.environ["DB_USER"],
            password=os.environ["DB_PASS"],
            connect_timeout=10,
        )
        logger.info("Database connection pool created successfully.")
    return _connection_pool


@contextmanager
def get_connection():
    """Yield a connection from the pool; return it when done."""
    p = _get_pool()
    conn = p.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        p.putconn(conn)


# ---------------------------------------------------------------------------
# Query Helpers
# ---------------------------------------------------------------------------


def execute_nl_query(question: str) -> list[dict]:
    """
    Convert a natural-language question into SQL using AlloyDB AI NL
    (`ecommerce_cfg` configuration) and execute it.

    Args:
        question: User's natural-language product question.

    Returns:
        A list of dicts, one per result row.
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
            # alloydb_ai_nl.textual_sql_query returns a JSONB result set
            cur.execute(
                "SELECT alloydb_ai_nl.textual_sql_query('ecommerce_cfg', %s) AS result;",
                (question,),
            )
            row = cur.fetchone()

            if row is None or row["result"] is None:
                return []

            result = row["result"]

            # The extension may return a JSON string or already-parsed object
            if isinstance(result, str):
                result = json.loads(result)

            # Normalize: could be a list or a dict with a "rows" key
            if isinstance(result, dict):
                result = result.get("rows", [result])
            if not isinstance(result, list):
                result = [result]

            return result


def execute_raw_query(sql: str, params: tuple | None = None) -> list[dict]:
    """
    Execute a raw SQL query and return rows as dicts.

    Args:
        sql:    SQL string (may contain %s placeholders).
        params: Optional tuple of parameters for the query.

    Returns:
        A list of dicts, one per result row.
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            if cur.description is None:
                return []
            return [dict(row) for row in cur.fetchall()]


def check_connection() -> bool:
    """Return True if the database is reachable."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                return True
    except Exception as e:
        logger.error("Database health check failed: %s", e)
        return False


def close_pool() -> None:
    """Close all connections in the pool (call on shutdown)."""
    global _connection_pool
    if _connection_pool is not None and not _connection_pool.closed:
        _connection_pool.closeall()
        logger.info("Database connection pool closed.")
        _connection_pool = None
