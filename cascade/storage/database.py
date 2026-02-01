import logging
import sqlite3
import time
from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# Register adapters for Python 3.12+ compatibility
def adapt_datetime(dt: datetime) -> str:
    return dt.isoformat()


def convert_datetime(val: bytes) -> datetime:
    return datetime.fromisoformat(val.decode())


sqlite3.register_adapter(datetime, adapt_datetime)
sqlite3.register_converter("timestamp", convert_datetime)
sqlite3.register_converter("datetime", convert_datetime)
sqlite3.register_converter("TIMESTAMP", convert_datetime)


class Database:
    """
    SQLite database manager for Cascade.

    Handles connection management, schema initialization, and provides
    a context manager for safe transactions.
    """

    def __init__(self, db_path: Path):
        """
        Initialize database connection.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._connection: sqlite3.Connection | None = None

    def initialize(self) -> None:
        """Create database and initialize schema."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        schema_path = Path(__file__).parent / "schemas.sql"

        with self.connection() as conn:
            with open(schema_path) as f:
                conn.executescript(f.read())
            conn.commit()

        logger.info(f"Database initialized at {self.db_path}")

    @contextmanager
    def connection(self) -> Generator[sqlite3.Connection, None, None]:
        """
        Get database connection as context manager.

        Enables foreign keys and returns Row objects for easier access.
        """
        conn = sqlite3.connect(
            self.db_path,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")

        try:
            yield conn
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @contextmanager
    def transaction(self) -> Generator[sqlite3.Connection, None, None]:
        """
        Execute operations in a transaction.

        Automatically commits on success, rolls back on failure.
        """
        with self.connection() as conn:
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    def execute(
        self, query: str, params: tuple[Any, ...] = (), *, fetch: bool = False
    ) -> list[sqlite3.Row] | None:
        """
        Execute a query and optionally fetch results.

        Args:
            query: SQL query string
            params: Query parameters
            fetch: Whether to fetch and return results

        Returns:
            List of rows if fetch=True, None otherwise
        """
        start_time = time.time()
        try:
            with self.transaction() as conn:
                cursor = conn.execute(query, params)
                if fetch:
                    return cursor.fetchall()
                return None
        finally:
            duration = time.time() - start_time
            if duration > 0.5:
                logger.warning(f"Slow query ({duration:.3f}s): {query}")

    def execute_many(self, query: str, params_list: list[tuple[Any, ...]]) -> None:
        """
        Execute a query multiple times with different parameters.

        Args:
            query: SQL query string
            params_list: List of parameter tuples
        """
        with self.transaction() as conn:
            conn.executemany(query, params_list)

    def fetch_one(self, query: str, params: tuple[Any, ...] = ()) -> sqlite3.Row | None:
        """
        Execute query and fetch single result.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            Single row or None
        """
        with self.connection() as conn:
            cursor = conn.execute(query, params)
            row = cursor.fetchone()
            return row if row else None

    def fetch_all(self, query: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        """
        Execute query and fetch all results.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            List of rows
        """
        with self.connection() as conn:
            cursor = conn.execute(query, params)
            return cursor.fetchall()

    def insert(self, table: str, data: dict[str, Any]) -> int:
        """
        Insert a row and return the new ID.

        Args:
            table: Table name
            data: Column name to value mapping

        Returns:
            ID of inserted row
        """
        columns = ", ".join(data.keys())
        placeholders = ", ".join("?" * len(data))
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"

        with self.transaction() as conn:
            cursor = conn.execute(query, tuple(data.values()))
            return cursor.lastrowid or 0

    def update(self, table: str, data: dict[str, Any], where: str, params: tuple[Any, ...]) -> int:
        """
        Update rows matching condition.

        Args:
            table: Table name
            data: Column name to value mapping
            where: WHERE clause (without 'WHERE')
            params: Parameters for WHERE clause

        Returns:
            Number of affected rows
        """
        set_clause = ", ".join(f"{k} = ?" for k in data.keys())
        query = f"UPDATE {table} SET {set_clause} WHERE {where}"
        all_params = tuple(data.values()) + params

        with self.transaction() as conn:
            cursor = conn.execute(query, all_params)
            return cursor.rowcount

    def delete(self, table: str, where: str, params: tuple[Any, ...]) -> int:
        """
        Delete rows matching condition.

        Args:
            table: Table name
            where: WHERE clause (without 'WHERE')
            params: Parameters for WHERE clause

        Returns:
            Number of deleted rows
        """
        query = f"DELETE FROM {table} WHERE {where}"

        with self.transaction() as conn:
            cursor = conn.execute(query, params)
            return cursor.rowcount

    def exists(self, table: str, where: str, params: tuple[Any, ...]) -> bool:
        """
        Check if any rows match condition.

        Args:
            table: Table name
            where: WHERE clause (without 'WHERE')
            params: Parameters for WHERE clause

        Returns:
            True if matching rows exist
        """
        query = f"SELECT 1 FROM {table} WHERE {where} LIMIT 1"
        result = self.fetch_one(query, params)
        return result is not None

    def count(self, table: str, where: str = "1=1", params: tuple[Any, ...] = ()) -> int:
        """
        Count rows matching condition.

        Args:
            table: Table name
            where: WHERE clause (without 'WHERE'), defaults to all rows
            params: Parameters for WHERE clause

        Returns:
            Row count
        """
        query = f"SELECT COUNT(*) FROM {table} WHERE {where}"
        result = self.fetch_one(query, params)
        return result[0] if result else 0


def get_database(project_root: Path) -> Database:
    """
    Get database instance for a project.

    Args:
        project_root: Root directory of the project

    Returns:
        Database instance
    """
    db_path = project_root / ".cascade" / "cascade.db"
    return Database(db_path)
