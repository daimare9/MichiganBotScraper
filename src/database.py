import sqlite3
from pathlib import Path

from .models import Contract


class ContractDatabase:
    """
    Thin SQLite wrapper used purely for deduplication.

    A contract's ``unique_key`` is stored the first time it is seen.
    Subsequent scrape cycles that encounter the same key will know not
    to re-send an email alert.
    """

    def __init__(self, db_path: str = "data/contracts.db") -> None:
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        # check_same_thread=False is safe here because the scheduler
        # runs all jobs sequentially in a single thread.
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS seen_contracts (
                unique_key  TEXT PRIMARY KEY,
                source      TEXT NOT NULL,
                title       TEXT NOT NULL,
                first_seen  TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        self._conn.commit()

    def is_new(self, contract: Contract) -> bool:
        """Return True if this contract has never been emailed before."""
        row = self._conn.execute(
            "SELECT 1 FROM seen_contracts WHERE unique_key = ?",
            (contract.unique_key,),
        ).fetchone()
        return row is None

    def mark_seen(self, contract: Contract) -> None:
        """Record a contract so it is never alerted again."""
        self._conn.execute(
            """
            INSERT OR IGNORE INTO seen_contracts (unique_key, source, title)
            VALUES (?, ?, ?)
            """,
            (contract.unique_key, contract.source, contract.title),
        )
        self._conn.commit()

    def total_seen(self) -> int:
        """Return the total number of contracts tracked in the database."""
        row = self._conn.execute("SELECT COUNT(*) FROM seen_contracts").fetchone()
        return row[0] if row else 0

    def close(self) -> None:
        self._conn.close()
