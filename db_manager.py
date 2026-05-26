"""Small SQLite helper retained for integrations importing DatabaseManager."""

from __future__ import annotations

import sqlite3


class DatabaseManager:
    def __init__(self, connection_string: str):
        self.database_path = connection_string.removeprefix("sqlite:///")
        self.connection: sqlite3.Connection | None = None

    def connect(self) -> bool:
        try:
            self.connection = sqlite3.connect(self.database_path)
            self.connection.row_factory = sqlite3.Row
            return True
        except sqlite3.Error:
            return False

    def disconnect(self) -> None:
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def _connection(self) -> sqlite3.Connection:
        if self.connection is None:
            raise RuntimeError("DatabaseManager is not connected.")
        return self.connection

    def get_all_tables(self) -> list[str]:
        rows = self._connection().execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
        )
        return [row["name"] for row in rows]

    def get_table_schema(self, table_name: str) -> dict:
        safe_name = table_name.replace('"', '""')
        columns = self._connection().execute(f'PRAGMA table_info("{safe_name}")').fetchall()
        return {
            "table_name": table_name,
            "columns": [
                {
                    "name": column["name"],
                    "type": column["type"],
                    "nullable": not bool(column["notnull"]),
                    "default": column["dflt_value"],
                }
                for column in columns
            ],
        }

    def execute_query(self, query: str, params: tuple | None = None):
        connection = self._connection()
        cursor = connection.execute(query, params or ())
        if cursor.description:
            return [dict(row) for row in cursor.fetchall()]
        connection.commit()
        return {"affected_rows": cursor.rowcount}
