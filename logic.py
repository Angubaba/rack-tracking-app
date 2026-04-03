"""Business logic for OK and TH scan validation."""
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Optional

import database
import settings
from utils import validate_rack_number


@dataclass
class ScanResult:
    success: bool
    message: str
    status: str = "success"   # 'success' | 'warning' | 'error'
    scan_id: Optional[int] = None


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _parse_utc(iso_str: str) -> datetime:
    dt = datetime.fromisoformat(iso_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def validate_ok_scan(
    rack_number: str,
    model: str,
    quantity: int,
    inspected_by: str,
) -> ScanResult:
    """Run all checks without writing to the database. Returns success=True if valid."""
    if not rack_number:
        return ScanResult(False, "Rack Number is required.", "error")
    if not validate_rack_number(rack_number):
        return ScanResult(
            False,
            f"Invalid format '{rack_number}'. Expected PR/### or MR/###.",
            "error",
        )
    if not model:
        return ScanResult(False, "Model is required.", "error")
    if not (1 <= quantity <= 10_000):
        return ScanResult(False, "Quantity must be between 1 and 10,000.", "error")
    if not inspected_by:
        return ScanResult(False, "Inspected By is required.", "error")

    if database.get_active_rack(rack_number):
        return ScanResult(
            False,
            f"Rack {rack_number} is already in FG. Send it to TH before re-scanning.",
            "error",
        )

    dup_minutes = settings.load()["duplicate_lock_minutes"]
    now = _now_utc()
    for scan in database.get_ok_scans_for_rack(rack_number):
        age = (now - _parse_utc(scan["created_at"])).total_seconds()
        if age < dup_minutes * 60:
            return ScanResult(
                False,
                f"Rack {rack_number} was scanned as OK less than {dup_minutes} minutes ago.",
                "error",
            )

    return ScanResult(True, "")


def perform_ok_scan(
    rack_number: str,
    model: str,
    quantity: int,
    inspected_by: str,
    pcb_ids: list | None = None,
) -> ScanResult:
    """Validate, insert OK scan, and optionally insert PCB samples."""
    result = validate_ok_scan(rack_number, model, quantity, inspected_by)
    if not result.success:
        return result

    scan_id = database.insert_ok_scan(rack_number, model, quantity, inspected_by)
    if pcb_ids:
        database.insert_pcb_samples(scan_id, pcb_ids)

    return ScanResult(True, f"Rack {rack_number} added to FG.", "success", scan_id)


def check_th_completion_lock(rack_number: str) -> ScanResult | None:
    """
    TH tab only — checks if this rack was sent to TH recently.
    Returns a confirm_required ScanResult if locked, None if clear.
    This is a SOFT lock — caller shows a confirmation dialog and proceeds if user agrees.
    Completely independent of the OK duplicate lock.
    """
    lock_minutes = settings.load()["completion_lock_minutes"]
    now = _now_utc()

    with database._connect() as conn:
        rows = conn.execute(
            "SELECT created_at FROM th_scans WHERE rack_number = ?"
            " ORDER BY created_at DESC LIMIT 1",
            (rack_number,),
        ).fetchone()

    if rows:
        age = (now - _parse_utc(rows["created_at"])).total_seconds()
        if age < lock_minutes * 60:
            return ScanResult(
                False,
                (
                    f"Rack {rack_number} was already sent to TH less than "
                    f"{lock_minutes} minutes ago.\n\nOverride and send again?"
                ),
                "confirm_required",
            )
    return None
