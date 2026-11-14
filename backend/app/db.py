"""
Talking to Postgres with psycopg2 and plain SQL, no ORM.

Every call opens a connection, does its work and closes it in a finally
block. `with connection:` in psycopg2 only ends the transaction; it does
not close the connection, so the close has to be explicit or connections
pile up until Postgres refuses new ones.
"""

import psycopg2
from psycopg2.extras import RealDictCursor

from . import config


def get_connection(dbname=None):
    return psycopg2.connect(
        dbname=dbname or config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        host=config.DB_HOST,
        port=config.DB_PORT,
        sslmode=config.DB_SSLMODE,
    )


def _run(sql, params, fetch):
    connection = get_connection()
    try:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            # None, not {}: with a dict, psycopg2 treats every % in the SQL
            # as a placeholder.
            cursor.execute(sql, params if params else None)
            result = None
            if fetch == "all":
                result = [dict(row) for row in cursor.fetchall()]
            elif fetch == "one":
                row = cursor.fetchone()
                result = dict(row) if row else None
        connection.commit()
        return result
    finally:
        connection.close()


def fetch_all(sql, params=None):
    return _run(sql, params, "all")


def fetch_one(sql, params=None):
    return _run(sql, params, "one")
