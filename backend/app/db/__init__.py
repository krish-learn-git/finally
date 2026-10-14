"""Database layer — sqlite3-based, synchronous, stdlib only."""

from .init import get_db, init_db

__all__ = ["get_db", "init_db"]
