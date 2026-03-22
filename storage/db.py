"""
storage/db.py

Supports both:
- PostgreSQL (Supabase) when DATABASE_URL is set — used in production/GitHub Actions
- SQLite when DATABASE_PATH is set — used locally
"""

import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/news_digest.db")


def get_connection():
    """
    Returns a database connection.
    Uses PostgreSQL if DATABASE_URL is set, otherwise SQLite.
    """
    if DATABASE_URL:
        import psycopg2
        import psycopg2.extras
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    else:
        import sqlite3
        db_path = Path(DATABASE_PATH)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_path), timeout=10)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        conn.row_factory = sqlite3.Row
        return conn


def is_postgres() -> bool:
    return bool(DATABASE_URL)


def init_db() -> None:
    """
    Initialize SQLite database from schema.sql.
    Only needed locally — Supabase schema is created via SQL Editor.
    """
    if is_postgres():
        logger.info("Using PostgreSQL — skipping local DB init.")
        return

    SCHEMA_PATH = Path(__file__).parent / "schema.sql"
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema file not found at: {SCHEMA_PATH}")

    logger.info("Initializing SQLite database at: %s", DATABASE_PATH)
    conn = get_connection()
    try:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        conn.commit()
        logger.info("SQLite database initialized successfully.")
    except Exception as e:
        logger.error("Failed to initialize database: %s", e)
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    init_db()
    print("Database successfully initialized.")