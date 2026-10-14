"""Database initialisation and connection factory using stdlib sqlite3."""

from __future__ import annotations

import logging
import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from ..utils import now_iso as _now

logger = logging.getLogger(__name__)

_DB_PATH: Path | None = None
_SCHEMA_SQL = (Path(__file__).parent / "schema.sql").read_text()

DEFAULT_TICKERS = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "NFLX"]


def configure(db_path: str | Path) -> None:
    """Set the database file path. Call once on app startup."""
    global _DB_PATH
    _DB_PATH = Path(db_path)
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Sync context manager yielding a configured sqlite3 connection."""
    assert _DB_PATH is not None, "Call init_db() before get_db()"
    conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: str | Path) -> None:
    """Create schema and seed default data if the database is empty. Synchronous."""
    configure(db_path)
    with get_db() as conn:
        conn.executescript(_SCHEMA_SQL)

        cursor = conn.execute("SELECT COUNT(*) FROM users_profile")
        if cursor.fetchone()[0] == 0:
            now = _now()
            conn.execute(
                "INSERT INTO users_profile (id, cash_balance, created_at) VALUES (?, ?, ?)",
                ("default", 10000.0, now),
            )
            for ticker in DEFAULT_TICKERS:
                conn.execute(
                    "INSERT INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
                    (str(uuid.uuid4()), "default", ticker, now),
                )
            logger.info("Database seeded with default user and watchlist")
        else:
            logger.info("Database already initialised — skipping seed")



