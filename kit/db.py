"""Database helpers: one pooled connection per request, plain SQL, dict rows."""
from contextlib import contextmanager

import psycopg2
import psycopg2.extras
import psycopg2.pool

from .config import get_settings

_pool = None


def pool():
    global _pool
    if _pool is None:
        _pool = psycopg2.pool.ThreadedConnectionPool(1, 8, get_settings().database_url)
    return _pool


@contextmanager
def connect(readonly: bool = False):
    p = pool()
    conn = p.getconn()
    try:
        conn.set_session(readonly=readonly)
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.set_session(readonly=False)
        p.putconn(conn)


def query(sql: str, params=None, conn=None) -> list[dict]:
    if conn is None:
        with connect(readonly=True) as c:
            return query(sql, params, c)
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, params or {})
        return [dict(r) for r in cur.fetchall()] if cur.description else []


def one(sql: str, params=None, conn=None) -> dict | None:
    rows = query(sql, params, conn)
    return rows[0] if rows else None


def execute(sql: str, params=None, conn=None) -> int:
    if conn is None:
        with connect() as c:
            return execute(sql, params, c)
    with conn.cursor() as cur:
        cur.execute(sql, params or {})
        return cur.rowcount
