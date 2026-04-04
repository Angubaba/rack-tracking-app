import sys
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def get_db_path() -> Path:
    if getattr(sys, "frozen", False):
        # Running as packaged .exe — store next to the exe
        base = Path(sys.executable).parent
    else:
        # Running as script — store next to main.py
        base = Path(__file__).parent
    base.mkdir(parents=True, exist_ok=True)
    return base / "rack_track.db"


DB_PATH = get_db_path()


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ok_scans (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                rack_number   TEXT    NOT NULL,
                model         TEXT    NOT NULL,
                quantity      INTEGER NOT NULL,
                inspected_by  TEXT    NOT NULL,
                created_at    TEXT    NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS th_scans (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                ok_scan_id    INTEGER NOT NULL REFERENCES ok_scans(id),
                rack_number   TEXT    NOT NULL,
                model         TEXT    NOT NULL,
                quantity      INTEGER NOT NULL,
                inspected_by  TEXT    NOT NULL,
                taken_by      TEXT    NOT NULL,
                created_at    TEXT    NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pcb_samples (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                ok_scan_id  INTEGER NOT NULL REFERENCES ok_scans(id),
                pcb_id      TEXT    NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ok_rack    ON ok_scans(rack_number)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ok_time    ON ok_scans(created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_th_ok_id   ON th_scans(ok_scan_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_pcb_ok_id  ON pcb_samples(ok_scan_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_th_rack    ON th_scans(rack_number)")
        conn.commit()


# ── OK scans ─────────────────────────────────────────────────────────────────

def insert_ok_scan(rack_number: str, model: str, quantity: int, inspected_by: str) -> int:
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO ok_scans (rack_number, model, quantity, inspected_by, created_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (rack_number, model, quantity, inspected_by, now),
        )
        conn.commit()
        return cur.lastrowid


def get_ok_scan_by_id(scan_id: int):
    with _connect() as conn:
        return conn.execute(
            "SELECT * FROM ok_scans WHERE id = ?", (scan_id,)
        ).fetchone()


def get_ok_scans_for_rack(rack_number: str) -> list:
    with _connect() as conn:
        return conn.execute(
            "SELECT * FROM ok_scans WHERE rack_number = ? ORDER BY created_at DESC",
            (rack_number,),
        ).fetchall()


def delete_ok_scan(scan_id: int) -> None:
    """Deletes the OK scan and all linked TH scan + PCB samples."""
    with _connect() as conn:
        conn.execute("DELETE FROM pcb_samples WHERE ok_scan_id = ?", (scan_id,))
        conn.execute("DELETE FROM th_scans   WHERE ok_scan_id = ?", (scan_id,))
        conn.execute("DELETE FROM ok_scans   WHERE id = ?",         (scan_id,))
        conn.commit()


# ── TH scans ─────────────────────────────────────────────────────────────────

def insert_th_scan(
    ok_scan_id: int, rack_number: str, model: str,
    quantity: int, inspected_by: str, taken_by: str,
) -> int:
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO th_scans"
            " (ok_scan_id, rack_number, model, quantity, inspected_by, taken_by, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (ok_scan_id, rack_number, model, quantity, inspected_by, taken_by, now),
        )
        conn.commit()
        return cur.lastrowid


def get_th_scan_by_id(scan_id: int):
    with _connect() as conn:
        return conn.execute(
            "SELECT * FROM th_scans WHERE id = ?", (scan_id,)
        ).fetchone()


def get_th_scan_for_ok(ok_scan_id: int):
    with _connect() as conn:
        return conn.execute(
            "SELECT * FROM th_scans WHERE ok_scan_id = ?", (ok_scan_id,)
        ).fetchone()


def delete_th_scan(scan_id: int) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM th_scans WHERE id = ?", (scan_id,))
        conn.commit()


# ── Active racks ─────────────────────────────────────────────────────────────

def get_active_racks() -> list:
    """OK scans that have no corresponding TH scan — currently in FG."""
    with _connect() as conn:
        return conn.execute("""
            SELECT ok_scans.*
            FROM ok_scans
            LEFT JOIN th_scans ON ok_scans.id = th_scans.ok_scan_id
            WHERE th_scans.id IS NULL
            ORDER BY ok_scans.created_at ASC
        """).fetchall()


def get_active_rack(rack_number: str):
    """Return the active OK scan for a rack, or None if not in FG."""
    with _connect() as conn:
        return conn.execute("""
            SELECT ok_scans.*
            FROM ok_scans
            LEFT JOIN th_scans ON ok_scans.id = th_scans.ok_scan_id
            WHERE th_scans.id IS NULL AND ok_scans.rack_number = ?
            ORDER BY ok_scans.created_at DESC LIMIT 1
        """, (rack_number,)).fetchone()


# ── Merged sequential events ─────────────────────────────────────────────────

def search_events(
    rack_number: Optional[str],
    utc_from: Optional[str],
    utc_to: Optional[str],
) -> list:
    """Merged OK + TH events, newest-first, with optional filters."""
    rack_clause = "AND rack_number = ?" if rack_number else ""
    from_clause = "AND created_at >= ?" if utc_from else ""
    to_clause   = "AND created_at <= ?" if utc_to else ""

    def params(*extras):
        p = []
        if rack_number: p.append(rack_number)
        if utc_from:    p.append(utc_from)
        if utc_to:      p.append(utc_to)
        return p + list(extras)

    sql = f"""
        SELECT 'OK' AS event_type,
               id, rack_number, model, quantity, inspected_by,
               '' AS taken_by, created_at
        FROM ok_scans
        WHERE 1=1 {rack_clause} {from_clause} {to_clause}
        UNION ALL
        SELECT 'TH' AS event_type,
               id, rack_number, model, quantity, inspected_by,
               taken_by, created_at
        FROM th_scans
        WHERE 1=1 {rack_clause} {from_clause} {to_clause}
        ORDER BY created_at DESC
    """
    with _connect() as conn:
        return conn.execute(sql, params() + params()).fetchall()


# ── PCB samples ───────────────────────────────────────────────────────────────

def insert_pcb_samples(ok_scan_id: int, pcb_ids: list) -> None:
    with _connect() as conn:
        conn.executemany(
            "INSERT INTO pcb_samples (ok_scan_id, pcb_id) VALUES (?, ?)",
            [(ok_scan_id, pid) for pid in pcb_ids],
        )
        conn.commit()


def get_pcb_samples(ok_scan_id: int) -> list:
    with _connect() as conn:
        return conn.execute(
            "SELECT pcb_id FROM pcb_samples WHERE ok_scan_id = ? ORDER BY id ASC",
            (ok_scan_id,),
        ).fetchall()


def get_all_pcb_ids_for_rack(rack_number: str) -> set:
    """Return every PCB ID ever recorded for this rack across all OK scans."""
    with _connect() as conn:
        rows = conn.execute("""
            SELECT p.pcb_id
            FROM pcb_samples p
            JOIN ok_scans o ON p.ok_scan_id = o.id
            WHERE o.rack_number = ?
        """, (rack_number,)).fetchall()
    return {r["pcb_id"] for r in rows}
