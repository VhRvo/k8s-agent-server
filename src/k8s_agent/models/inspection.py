import os
import sqlite3
import threading
import uuid
from typing import Optional


class InspectionStore:
    def __init__(self, db_path: str = "data/inspections.db", max_records: int = 50):
        self._db_path = db_path
        self._max_records = max_records
        self._lock = threading.Lock()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init(self, db_path: str | None = None, max_records: int | None = None) -> None:
        if db_path is not None:
            self._db_path = db_path
        if max_records is not None:
            self._max_records = max_records
        os.makedirs(os.path.dirname(self._db_path) or ".", exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS inspections (
                    id        TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    trigger   TEXT NOT NULL,
                    status    TEXT NOT NULL,
                    response  TEXT DEFAULT '',
                    error     TEXT DEFAULT ''
                )"""
            )

    def insert(self, timestamp: str, trigger: str) -> str:
        rid = str(uuid.uuid4())[:8]
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO inspections (id, timestamp, trigger, status) VALUES (?, ?, ?, 'running')",
                (rid, timestamp, trigger),
            )
            self._trim(conn)
        return rid

    def update(self, record_id: str, **fields) -> None:
        allowed = {"status", "response", "error"}
        sets = [f"{k}=?" for k in fields if k in allowed]
        vals = [v for k, v in fields.items() if k in allowed]
        if not sets:
            return
        vals.append(record_id)
        with self._lock, self._connect() as conn:
            conn.execute(f"UPDATE inspections SET {', '.join(sets)} WHERE id=?", vals)

    def get(self, record_id: str) -> Optional[dict]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM inspections WHERE id=?", (record_id,)
            ).fetchone()
            return dict(row) if row else None

    def list(self) -> list:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM inspections ORDER BY timestamp DESC"
            ).fetchall()
            return [dict(r) for r in rows]

    def _trim(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            "DELETE FROM inspections WHERE id NOT IN "
            "(SELECT id FROM inspections ORDER BY timestamp DESC LIMIT ?)",
            (self._max_records,),
        )


store = InspectionStore()
