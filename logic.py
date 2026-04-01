"""Business logic: validation, lock, duplicate prevention."""
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from typing import Optional

import database
import settings
from utils import validate_rack_number


@dataclass
class ScanResult:
    success: bool
    message: str
    # 'success' | 'warning' | 'error' | 'confirm_required'
    status: str = "success"
    scan_id: Optional[int] = None


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _parse_utc(iso_str: str) -> datetime:
    dt = datetime.fromisoformat(iso_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _is_duplicate(rack_number: str, model: str) -> bool:
    """Hard block: same rack + same model scanned within duplicate_lock_minutes."""
    dup_minutes = settings.load()["duplicate_lock_minutes"]
    now = _now_utc()
    for scan in database.get_rack_scans(rack_number):
        if scan["model"] == model:
            age = (now - _parse_utc(scan["created_at"])).total_seconds()
            if age < dup_minutes * 60:
                return True
    return False


def _is_locked(rack_number: str) -> bool:
    """Completion lock: rack was scanned within completion_lock_minutes."""
    lock_minutes = settings.load()["completion_lock_minutes"]
    last = database.get_rack_last_scan(rack_number)
    if last:
        age = (_now_utc() - _parse_utc(last["created_at"])).total_seconds()
        if age < lock_minutes * 60:
            return True
    return False


def perform_scan(
    rack_number: str,
    model: str,
    quantity: int,
    inspected_by: str,
    override: bool = False,
) -> ScanResult:
    """
    Attempt to record a scan.

    If status == 'confirm_required', caller should prompt and retry with override=True.
    """
    # ── field validation ────────────────────────────────────────────────────
    if not rack_number:
        return ScanResult(False, "Rack Number is required.", "error")
    if not validate_rack_number(rack_number):
        return ScanResult(
            False,
            f"Invalid rack format: '{rack_number}'.\nExpected PR/### or MR/### (e.g. PR/042, MR/7).",
            "error",
        )
    if not model:
        return ScanResult(False, "Model is required.", "error")
    if len(model) > 64:
        return ScanResult(False, "Model must be 64 characters or fewer.", "error")
    if not (1 <= quantity <= 10_000):
        return ScanResult(False, "Quantity must be between 1 and 10,000.", "error")
    if not inspected_by:
        return ScanResult(False, "Inspected By is required.", "error")
    if len(inspected_by) > 64:
        return ScanResult(False, "Inspected By must be 64 characters or fewer.", "error")

    # ── duplicate block (hard — no override) ────────────────────────────────
    dup_minutes  = settings.load()["duplicate_lock_minutes"]
    lock_minutes = settings.load()["completion_lock_minutes"]

    if _is_duplicate(rack_number, model):
        return ScanResult(
            False,
            (
                f"Duplicate scan blocked: rack {rack_number} with model {model} "
                f"was already scanned within the last {dup_minutes} minutes."
            ),
            "error",
        )

    # ── completion lock (soft — override allowed) ───────────────────────────
    if not override and _is_locked(rack_number):
        return ScanResult(
            False,
            (
                f"Rack {rack_number} was scanned less than {lock_minutes} minutes ago.\n\n"
                f"Override and scan anyway?"
            ),
            "confirm_required",
        )

    # ── record ──────────────────────────────────────────────────────────────
    scan_id = database.insert_scan(rack_number, model, quantity, inspected_by)

    return ScanResult(
        True,
        f"Scan recorded: {rack_number}  ·  {model}  ·  Qty {quantity}",
        "success",
        scan_id,
    )
