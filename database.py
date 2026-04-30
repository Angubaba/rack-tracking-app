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
            CREATE TABLE IF NOT EXISTS smt_handovers (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                rack_number  TEXT    NOT NULL,
                model        TEXT    NOT NULL,
                quantity     INTEGER NOT NULL,
                smt_operator TEXT    NOT NULL,
                line         TEXT    NOT NULL DEFAULT '',
                created_at   TEXT    NOT NULL,
                status       TEXT    NOT NULL DEFAULT 'PENDING',
                processed_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ok_scans (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                rack_number      TEXT    NOT NULL,
                model            TEXT    NOT NULL,
                quantity         INTEGER NOT NULL,
                inspected_by     TEXT    NOT NULL,
                created_at       TEXT    NOT NULL,
                smt_handover_id  INTEGER REFERENCES smt_handovers(id)
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
        # Migrations for schema additions
        for migration in [
            "ALTER TABLE ok_scans ADD COLUMN smt_handover_id INTEGER REFERENCES smt_handovers(id)",
            "ALTER TABLE smt_handovers ADD COLUMN line TEXT NOT NULL DEFAULT ''",
            "ALTER TABLE smt_handovers ADD COLUMN not_ok_reason TEXT NOT NULL DEFAULT ''",
            "ALTER TABLE smt_handovers ADD COLUMN cards INTEGER",
            "ALTER TABLE ok_scans ADD COLUMN cards INTEGER",
            "ALTER TABLE th_scans ADD COLUMN cards INTEGER",
        ]:
            try:
                conn.execute(migration)
            except Exception:
                pass  # Column already exists

        conn.execute("""
            CREATE TABLE IF NOT EXISTS trolley_scans (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                type        TEXT    NOT NULL,
                identifier  TEXT    NOT NULL,
                model       TEXT    NOT NULL,
                quantity    INTEGER NOT NULL,
                cards       INTEGER,
                taken_by    TEXT    NOT NULL,
                created_at  TEXT    NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_smt_rack    ON smt_handovers(rack_number)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_smt_status  ON smt_handovers(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ok_rack     ON ok_scans(rack_number)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ok_time     ON ok_scans(created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ok_smt_id   ON ok_scans(smt_handover_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_th_ok_id    ON th_scans(ok_scan_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_pcb_ok_id   ON pcb_samples(ok_scan_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_th_rack     ON th_scans(rack_number)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_trl_model   ON trolley_scans(model)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_trl_time    ON trolley_scans(created_at)")
        conn.commit()


# ── OK scans ─────────────────────────────────────────────────────────────────

def insert_ok_scan(rack_number: str, model: str, quantity: int, inspected_by: str,
                   cards: int = None) -> int:
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO ok_scans (rack_number, model, quantity, inspected_by, created_at, cards)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (rack_number, model, quantity, inspected_by, now, cards),
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
        ok_row = conn.execute(
            "SELECT cards FROM ok_scans WHERE id = ?", (ok_scan_id,)
        ).fetchone()
        cards = ok_row["cards"] if ok_row else None
        cur = conn.execute(
            "INSERT INTO th_scans"
            " (ok_scan_id, rack_number, model, quantity, inspected_by, taken_by, created_at, cards)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (ok_scan_id, rack_number, model, quantity, inspected_by, taken_by, now, cards),
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


# ── SMT Handovers ─────────────────────────────────────────────────────────────

def insert_smt_handover(rack_number: str, model: str, quantity: int,
                        smt_operator: str, line: str = "",
                        cards: int = None) -> int:
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO smt_handovers"
            " (rack_number, model, quantity, smt_operator, line, created_at, cards)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (rack_number, model, quantity, smt_operator, line, now, cards),
        )
        conn.commit()
        return cur.lastrowid


def get_pending_for_qc() -> list:
    """All SMT handovers with status PENDING, oldest first."""
    with _connect() as conn:
        return conn.execute(
            "SELECT * FROM smt_handovers WHERE status = 'PENDING' ORDER BY created_at ASC"
        ).fetchall()


def get_pending_rack(rack_number: str):
    """Return the PENDING smt_handover for a rack, or None."""
    with _connect() as conn:
        return conn.execute(
            "SELECT * FROM smt_handovers WHERE rack_number = ? AND status = 'PENDING' LIMIT 1",
            (rack_number,),
        ).fetchone()


def mark_qc_ok(
    smt_handover_id: int, rack_number: str, model: str,
    quantity: int, inspected_by: str, pcb_ids: list,
) -> int:
    """Mark an SMT handover as OK, create the linked ok_scan, insert PCB samples."""
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        smt_row = conn.execute(
            "SELECT cards FROM smt_handovers WHERE id = ?", (smt_handover_id,)
        ).fetchone()
        cards = smt_row["cards"] if smt_row else None
        conn.execute(
            "UPDATE smt_handovers SET status='OK', processed_at=? WHERE id=?",
            (now, smt_handover_id),
        )
        cur = conn.execute(
            "INSERT INTO ok_scans"
            " (rack_number, model, quantity, inspected_by, created_at, smt_handover_id, cards)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (rack_number, model, quantity, inspected_by, now, smt_handover_id, cards),
        )
        ok_scan_id = cur.lastrowid
        if pcb_ids:
            conn.executemany(
                "INSERT INTO pcb_samples (ok_scan_id, pcb_id) VALUES (?, ?)",
                [(ok_scan_id, pid) for pid in pcb_ids],
            )
        conn.commit()
        return ok_scan_id


def mark_qc_not_ok(smt_handover_id: int, reason: str = "") -> None:
    """Mark an SMT handover as NOT_OK (rack returned to SMT)."""
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        conn.execute(
            "UPDATE smt_handovers SET status='NOT_OK', processed_at=?, not_ok_reason=? WHERE id=?",
            (now, reason, smt_handover_id),
        )
        conn.commit()


def undo_qc_ok(smt_handover_id: int, ok_scan_id: int) -> None:
    """Undo a QC OK decision: delete ok_scan and reset smt_handover to PENDING."""
    with _connect() as conn:
        conn.execute("DELETE FROM pcb_samples WHERE ok_scan_id = ?", (ok_scan_id,))
        conn.execute("DELETE FROM th_scans   WHERE ok_scan_id = ?", (ok_scan_id,))
        conn.execute("DELETE FROM ok_scans   WHERE id = ?",         (ok_scan_id,))
        conn.execute(
            "UPDATE smt_handovers SET status='PENDING', processed_at=NULL WHERE id=?",
            (smt_handover_id,),
        )
        conn.commit()


def undo_qc_not_ok(smt_handover_id: int) -> None:
    """Undo a QC NOT OK decision: reset smt_handover to PENDING."""
    with _connect() as conn:
        conn.execute(
            "UPDATE smt_handovers SET status='PENDING', processed_at=NULL WHERE id=?",
            (smt_handover_id,),
        )
        conn.commit()


def delete_smt_handover(smt_id: int) -> None:
    """Delete an SMT handover and all linked ok_scan / pcb_samples / th_scan."""
    with _connect() as conn:
        ok_row = conn.execute(
            "SELECT id FROM ok_scans WHERE smt_handover_id = ?", (smt_id,)
        ).fetchone()
        if ok_row:
            conn.execute("DELETE FROM pcb_samples WHERE ok_scan_id = ?", (ok_row["id"],))
            conn.execute("DELETE FROM th_scans   WHERE ok_scan_id = ?", (ok_row["id"],))
            conn.execute("DELETE FROM ok_scans   WHERE id = ?",         (ok_row["id"],))
        conn.execute("DELETE FROM smt_handovers WHERE id = ?", (smt_id,))
        conn.commit()


def get_smt_handover_by_id(smt_id: int):
    with _connect() as conn:
        return conn.execute(
            "SELECT * FROM smt_handovers WHERE id = ?", (smt_id,)
        ).fetchone()


# ── Trolley / Tray scans ─────────────────────────────────────────────────────

def insert_trolley_scan(type_: str, identifier: str, model: str,
                        quantity: int, taken_by: str, cards: int = None) -> int:
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO trolley_scans (type, identifier, model, quantity, taken_by, created_at, cards)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (type_, identifier, model, quantity, taken_by, now, cards),
        )
        conn.commit()
        return cur.lastrowid


def delete_trolley_scan(scan_id: int) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM trolley_scans WHERE id = ?", (scan_id,))
        conn.commit()


# ── Cycle lookup ─────────────────────────────────────────────────────────────

def get_cycles(
    rack_number: Optional[str] = None,
    utc_from: Optional[str] = None,
    utc_to: Optional[str] = None,
    model: Optional[str] = None,
) -> list:
    """
    Return all rack cycles (SMT → QC → TH) as dicts, newest first.
    Also includes legacy ok_scans that have no SMT handover.

    Each dict has:
      cycle_type, rack_number, model, quantity,
      smt_id, smt_operator, smt_time,
      qc_result ('PENDING'|'OK'|'NOT_OK'|'LEGACY'),
      ok_scan_id, qc_inspector, qc_time,
      th_id, th_taken_by, th_time,
      sort_time (for ordering)
    """
    results = []

    def _wheres_params(alias_rack: str, alias_model: str, time_aliases: list):
        """Build WHERE clause. Date filter matches if ANY of time_aliases falls in range."""
        wheres, params = ["1=1"], []
        if rack_number:
            wheres.append(f"{alias_rack} = ?")
            params.append(rack_number)
        if model:
            wheres.append(f"UPPER({alias_model}) LIKE UPPER(?)")
            params.append(f"%{model}%")
        if utc_from or utc_to:
            time_conds, time_params = [], []
            for t in time_aliases:
                parts = []
                if utc_from:
                    parts.append(f"{t} >= ?")
                    time_params.append(utc_from)
                if utc_to:
                    parts.append(f"{t} <= ?")
                    time_params.append(utc_to)
                time_conds.append(f"({' AND '.join(parts)})")
            wheres.append(f"({' OR '.join(time_conds)})")
            params.extend(time_params)
        return " AND ".join(wheres), params

    with _connect() as conn:
        # ── New cycles — show if ANY of SMT/QC/TH timestamp falls in range ───
        where, params = _wheres_params(
            "sh.rack_number", "sh.model",
            ["sh.created_at", "os.created_at", "ts.created_at"],
        )
        rows = conn.execute(f"""
            SELECT
                sh.id          AS smt_id,
                sh.rack_number, sh.model, sh.quantity,
                sh.smt_operator, sh.line, sh.created_at AS smt_time,
                sh.status      AS qc_result, sh.not_ok_reason,
                os.id          AS ok_scan_id,
                os.inspected_by AS qc_inspector,
                os.created_at  AS qc_time,
                ts.id          AS th_id,
                ts.taken_by    AS th_taken_by,
                ts.created_at  AS th_time,
                COALESCE(ts.cards, os.cards, sh.cards) AS cards
            FROM smt_handovers sh
            LEFT JOIN ok_scans os ON os.smt_handover_id = sh.id
            LEFT JOIN th_scans ts ON ts.ok_scan_id = os.id
            WHERE {where}
            ORDER BY COALESCE(ts.created_at, os.created_at, sh.created_at) DESC
        """, params).fetchall()
        for r in rows:
            d = dict(r)
            d["cycle_type"] = "smt"
            d["sort_time"]  = d["th_time"] or d["qc_time"] or d["smt_time"] or ""
            results.append(d)

        # ── Legacy cycles — show if QC or TH timestamp falls in range ─────────
        where_leg, params_leg = _wheres_params(
            "os.rack_number", "os.model",
            ["os.created_at", "ts.created_at"],
        )
        leg_rows = conn.execute(f"""
            SELECT
                os.id          AS ok_scan_id,
                os.rack_number, os.model, os.quantity,
                os.inspected_by AS qc_inspector,
                os.created_at  AS qc_time,
                ts.id          AS th_id,
                ts.taken_by    AS th_taken_by,
                ts.created_at  AS th_time,
                COALESCE(ts.cards, os.cards) AS cards
            FROM ok_scans os
            LEFT JOIN th_scans ts ON ts.ok_scan_id = os.id
            WHERE os.smt_handover_id IS NULL AND {where_leg}
            ORDER BY COALESCE(ts.created_at, os.created_at) DESC
        """, params_leg).fetchall()
        for r in leg_rows:
            d = dict(r)
            d["cycle_type"]    = "legacy"
            d["smt_id"]        = None
            d["smt_operator"]  = ""
            d["line"]          = ""
            d["smt_time"]      = None
            d["qc_result"]     = "LEGACY"
            d["not_ok_reason"] = ""
            d["sort_time"]     = d["th_time"] or d["qc_time"] or ""
            results.append(d)

        # ── Trolley / Tray direct-TH records ─────────────────────────────────
        tr_wheres, tr_params = [], []
        if rack_number:
            tr_wheres.append("identifier = ?")
            tr_params.append(rack_number)
        if model:
            tr_wheres.append("UPPER(model) LIKE UPPER(?)")
            tr_params.append(f"%{model}%")
        if utc_from or utc_to:
            parts = []
            if utc_from:
                parts.append("created_at >= ?")
                tr_params.append(utc_from)
            if utc_to:
                parts.append("created_at <= ?")
                tr_params.append(utc_to)
            tr_wheres.append(f"({' AND '.join(parts)})")
        tr_where = ("WHERE " + " AND ".join(tr_wheres)) if tr_wheres else ""
        tr_rows = conn.execute(
            f"SELECT * FROM trolley_scans {tr_where} ORDER BY created_at DESC",
            tr_params,
        ).fetchall()
        for r in tr_rows:
            d = dict(r)
            results.append({
                'cycle_type':    'trolley',
                'trolley_id':    d['id'],
                'smt_id':        None,
                'rack_number':   d['identifier'],
                'model':         d['model'],
                'quantity':      d['quantity'],
                'smt_operator':  '',
                'line':          '',
                'smt_time':      None,
                'qc_result':     d['type'],        # 'TROLLEY' or 'TRAY'
                'not_ok_reason': '',
                'ok_scan_id':    None,
                'qc_inspector':  '',
                'qc_time':       None,
                'th_id':         d['id'],          # truthy → dashboard counts as TH
                'th_taken_by':   d['taken_by'],
                'th_time':       d['created_at'],
                'cards':         d['cards'],
                'sort_time':     d['created_at'],
            })

    results.sort(key=lambda x: x["sort_time"], reverse=True)
    return results
