"""Internal database connection management."""

import sqlite3
from pathlib import Path

from ukgeolocate.exceptions import DatabaseInvalid, DatabaseNotFound


class _DatabasePool:
    """
    Manages a read-only SQLite connection with reuse.

    SQLite in WAL mode supports concurrent readers, so holding a
    connection open across requests is safe and avoids the overhead
    of repeated open/close cycles.
    """

    def __init__(self, path: Path, name: str):
        self._path = path
        self._name = name
        self._conn: sqlite3.Connection | None = None

    def get_connection(self) -> sqlite3.Connection:
        """Return an open read-only connection, creating one if needed."""
        if self._conn is None:
            self._open()
        return self._conn

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """
        Execute a query, reconnecting if the database has gone stale.

        In a long-running process the DB file could be deleted or
        replaced after the initial connection was opened. This catches
        the resulting OperationalError and raises DatabaseNotFound so
        callers get a clean, expected exception.
        """
        conn = self.get_connection()
        try:
            return conn.execute(sql, params)
        except sqlite3.OperationalError:
            # Connection may be stale — check if the file still exists
            if not self._path.is_file():
                self.close()
                raise DatabaseNotFound(str(self._path), self._name)
            raise  # genuine query error, not a missing file

    def _open(self) -> None:
        """Open a fresh read-only connection."""
        if not self._path.is_file():
            raise DatabaseNotFound(str(self._path), self._name)
        self._conn = sqlite3.connect(
            f"file:{self._path}?mode=ro", uri=True
        )
        self._conn.execute("PRAGMA query_only = ON")

    def validate_tables(self, expected: list[str]) -> None:
        """
        Check that the database contains the expected tables.

        Raises DatabaseInvalid if any are missing.
        """
        cur = self.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        actual = {row[0] for row in cur}
        missing = set(expected) - actual
        if missing:
            raise DatabaseInvalid(
                str(self._path),
                f"missing tables: {', '.join(sorted(missing))}",
            )

    def close(self) -> None:
        """Close the connection if open."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None
