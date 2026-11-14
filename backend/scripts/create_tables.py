"""
Create the database (if missing) and every table.

    python -m scripts.create_tables            create what is missing
    python -m scripts.create_tables --reset    drop every table first

The DDL comes straight from pipeline/dictionary.py (the same text as
output/<scale>/sql/schema.sql), so the database always matches the
dictionary. --reset matters while the schema changes: CREATE TABLE IF
NOT EXISTS will not add a column to a table that already exists.
"""

import argparse
import sys

import psycopg2
from psycopg2 import sql

from app import config, db
from pipeline import export


def ensure_database():
    connection = db.get_connection("postgres")
    connection.autocommit = True  # CREATE DATABASE cannot run in a transaction
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (config.DB_NAME,))
            if cursor.fetchone() is None:
                cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(config.DB_NAME)))
                print(f"Created database {config.DB_NAME}.")
    finally:
        connection.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Create the database and tables.")
    parser.add_argument("--reset", action="store_true", help="Drop every table first.")
    args = parser.parse_args(argv)

    try:
        ensure_database()
    except psycopg2.OperationalError as error:
        print(f"Could not reach Postgres: {error}".strip())
        print("Check DB_HOST, DB_PORT, DB_USER and DB_PASSWORD in backend/.env.")
        return 1

    connection = db.get_connection()
    try:
        with connection.cursor() as cursor:
            if args.reset:
                cursor.execute(export.drop_sql())
            cursor.execute(export.schema_sql())
        connection.commit()
    finally:
        connection.close()
    print("Tables are ready.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
