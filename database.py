import sys
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def get_db_path() -> Path:
    """Return path to database file.
    When frozen by PyInstaller, stores in %APPDATA%\\RackTracker\\.
    During development, stores next to the script.
    """
    if getattr(sys, "frozen", False):
        import os
        base = Path(os.environ.get("APPDATA", Path.home())) / "RackTracker"
    else:
        base = Path(__file__).parent
    base.mkdir(parents=True, exist_ok=True)
    return base / "rack_track.db"


DB_PATH = get_db_path()


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS rack_scans (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                rack_number   TEXT    NOT NULL,
                model         TEXT    NOT NULL,
                quantity      INTEGER NOT NULL,
                inspected_by  TEXT    NOT NULL,
                created_at    TEXT    NOT NULL
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_rack_number ON rack_scans(rack_number)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_created_at  ON rack_scans(created_at)"
        )
        conn.commit()


def insert_scan(
    rack_number: str,
    model: str,
    quantity: int,
    inspected_by: str,
) -> int:
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        cur = conn.execute(
            """INSERT INTO rack_scans (rack_number, model, quantity, inspected_by, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (rack_number, model, quantity, inspected_by, now),
        )
        conn.commit()
        return cur.lastrowid


def get_recent_scans(limit: int = 10) -> list:
    with _connect() as conn:
        return conn.execute(
            "SELECT * FROM rack_scans ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()


def get_rack_scans(rack_number: str) -> list:
    with _connect() as conn:
        return conn.execute(
            "SELECT * FROM rack_scans WHERE rack_number = ? ORDER BY created_at DESC",
            (rack_number,),
        ).fetchall()


def search_scans(
    rack_number: str | None,
    utc_from: str | None,
    utc_to: str | None,
) -> list:
    """Flexible search: all params optional. utc_from/utc_to are ISO strings."""
    clauses = []
    params = []
    if rack_number:
        clauses.append("rack_number = ?")
        params.append(rack_number)
    if utc_from:
        clauses.append("created_at >= ?")
        params.append(utc_from)
    if utc_to:
        clauses.append("created_at <= ?")
        params.append(utc_to)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    with _connect() as conn:
        return conn.execute(
            f"SELECT * FROM rack_scans {where} ORDER BY created_at DESC",
            params,
        ).fetchall()


def get_rack_last_scan(rack_number: str):
    with _connect() as conn:
        return conn.execute(
            "SELECT * FROM rack_scans WHERE rack_number = ? ORDER BY created_at DESC LIMIT 1",
            (rack_number,),
        ).fetchone()


def get_scan_by_id(scan_id: int):
    with _connect() as conn:
        return conn.execute(
            "SELECT * FROM rack_scans WHERE id = ?", (scan_id,)
        ).fetchone()


def delete_scan(scan_id: int) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM rack_scans WHERE id = ?", (scan_id,))
        conn.commit()
