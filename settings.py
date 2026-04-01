import json
from database import get_db_path

_SETTINGS_PATH = get_db_path().parent / "settings.json"

DEFAULTS = {
    "duplicate_lock_minutes":   10,   # OK tab — hard block, same rack re-scanned as OK
    "completion_lock_minutes":  10,   # TH tab — soft block, rack already sent to TH recently
}


def load() -> dict:
    try:
        data = json.loads(_SETTINGS_PATH.read_text())
        return {**DEFAULTS, **data}
    except Exception:
        return dict(DEFAULTS)


def save(data: dict) -> None:
    _SETTINGS_PATH.write_text(json.dumps({**DEFAULTS, **data}, indent=2))
