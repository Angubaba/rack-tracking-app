import re
from datetime import datetime, timezone, timedelta

IST_OFFSET = timedelta(hours=5, minutes=30)

RACK_PATTERN = re.compile(r"^(PR|MR)/\d+$|^T\d+$|^TRAY$", re.IGNORECASE)


def to_ist(utc_iso_str: str) -> str:
    """Convert UTC ISO string to IST formatted string DD/MM/YYYY HH:MM:SS."""
    try:
        dt = datetime.fromisoformat(utc_iso_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        ist = dt + IST_OFFSET
        return ist.strftime("%d/%m/%Y %H:%M:%S")
    except (ValueError, AttributeError):
        return utc_iso_str


def now_ist_display() -> str:
    """Current time formatted in IST for display."""
    return to_ist(datetime.now(timezone.utc).isoformat())


def normalise_rack_number(rack_id: str) -> str:
    """Keep only alphanumeric and slash, strip everything else (whitespace, scanner garbage)."""
    import re
    return re.sub(r'[^A-Za-z0-9/]', '', rack_id).upper()


def validate_rack_number(rack_id: str) -> bool:
    """Return True if rack number matches PR/XXX or MR/XXX (XXX = digits)."""
    return bool(RACK_PATTERN.match(rack_id))
