"""
Database connection and query helper for AlloyDB.

Uses psycopg2 with connection pooling. All credentials are sourced
from environment variables to support Cloud Run deployment.

Supports two query modes:
1. AlloyDB AI NL (alloydb_ai_nl extension) — natural language to SQL
2. Fallback SQL — keyword/price-based search using ILIKE
"""

import os
import json
import logging
import re
from contextlib import contextmanager
from decimal import Decimal

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
    Try AlloyDB AI NL first; if unavailable, fall back to keyword search.

    Args:
        question: User's natural-language product question.

    Returns:
        A list of dicts, one per result row.
    """
    # Try alloydb_ai_nl first
    try:
        return _nl_query(question)
    except Exception as e:
        logger.warning(
            "alloydb_ai_nl query failed (falling back to SQL search): %s", e
        )
        # Fallback to keyword-based SQL search
        return _fallback_search(question)


def _nl_query(question: str) -> list[dict]:
    """Use alloydb_ai_nl extension to convert NL to SQL."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
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


def _fallback_search(question: str) -> list[dict]:
    """
    Fallback search using SQL ILIKE and price filters.
    Parses the question for keywords, categories, and price constraints.
    """
    question_lower = question.lower()

    conditions = []
    params = []

    # Extract price constraints
    price_match = re.search(
        r'(?:under|below|less than|cheaper than|max|up to|under rs|under ₹)\s*(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d{2})?)',
        question_lower,
    )
    if price_match:
        max_price = float(price_match.group(1))
        conditions.append("price <= %s")
        params.append(max_price)

    # Extract "above/over/more than ₹X"
    price_above = re.search(
        r'(?:above|over|more than|at least|min|starting|above rs|above ₹)\s*(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d{2})?)',
        question_lower,
    )
    if price_above:
        min_price = float(price_above.group(1))
        conditions.append("price >= %s")
        params.append(min_price)

    # Extract category keywords
    categories = ["electronics", "clothing", "home", "sports", "books"]
    for cat in categories:
        if cat in question_lower:
            conditions.append("LOWER(category) = %s")
            params.append(cat)

    # Extract search keywords (remove common stop words and price terms)
    stop_words = {
        "show", "me", "find", "search", "list", "get", "what", "which",
        "the", "a", "an", "is", "are", "do", "you", "have", "all",
        "products", "items", "things", "stuff", "under", "below", "above",
        "over", "less", "more", "than", "cheapest", "cheap", "expensive",
        "best", "top", "for", "and", "or", "in", "with", "to", "of",
        "price", "priced", "cost", "costs", "between", "from",
    }

    # Remove price patterns before extracting keywords
    cleaned = re.sub(r'(?:₹|rs\.?|inr)?\s*\d+(?:\.\d{2})?', '', question_lower)
    words = [w.strip("?!.,") for w in cleaned.split() if w.strip("?!.,")]
    keywords = [w for w in words if w not in stop_words and len(w) > 2]

    for keyword in keywords:
        conditions.append(
            "(LOWER(name) LIKE %s OR LOWER(description) LIKE %s OR LOWER(category) LIKE %s)"
        )
        pattern = f"%{keyword}%"
        params.extend([pattern, pattern, pattern])

    # Build query
    where_clause = " AND ".join(conditions) if conditions else "TRUE"

    sql = f"""
        SELECT id, name, description, category, price
        FROM products
        WHERE {where_clause}
        ORDER BY price ASC
        LIMIT 20;
    """

    logger.info("Fallback SQL: %s | params: %s", sql.strip(), params)

    return execute_raw_query(sql, tuple(params) if params else None)


def execute_raw_query(sql: str, params: tuple | None = None) -> list[dict]:
    """
    Execute a raw SQL query and return rows as dicts.
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            if cur.description is None:
                return []
            # Convert Decimal to float for JSON serialization
            rows = []
            for row in cur.fetchall():
                row_dict = dict(row)
                for key, value in row_dict.items():
                    if isinstance(value, Decimal):
                        row_dict[key] = float(value)
                rows.append(row_dict)
            return rows


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
