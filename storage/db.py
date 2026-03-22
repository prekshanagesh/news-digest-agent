import sqlite3
import logging
from pathlib import Path

from app.config import DATABASE_PATH

logger = logging.getLogger(__name__)

# Resolve schema.sql relative to this file, not the working directory
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def get_connection() -> sqlite3.Connection:
    """
    Return a SQLite connection to the configured database.
    Enables WAL mode for better concurrent read performance and
    sets a busy timeout so concurrent writes don't immediately fail.
    """
    if not DATABASE_PATH:
        raise EnvironmentError(
            "DATABASE_PATH is not set. Check your .env file."
        )

    # Ensure the parent directory exists (e.g. data/ folder)
    db_path = Path(DATABASE_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path), timeout=10)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """
    Initialize the database by running schema.sql.
    Safe to call multiple times — all CREATE TABLE statements use IF NOT EXISTS.
    """
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(
            f"Schema file not found at: {SCHEMA_PATH}. "
            "Make sure schema.sql is in the storage/ directory."
        )

    logger.info("Initializing database at: %s", DATABASE_PATH)

    conn = get_connection()
    try:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        conn.commit()
        logger.info("Database initialized successfully.")
    except sqlite3.Error as e:
        logger.error("Failed to initialize database: %s", e)
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    init_db()
    print("Database successfully initialized.")