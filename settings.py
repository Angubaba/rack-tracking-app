import json
from database import get_db_path

_SETTINGS_PATH = get_db_path().parent / "settings.json"

PERMANENT_PASSWORD = "1921"

DEFAULTS = {
    "duplicate_lock_minutes":   10,
    "completion_lock_minutes":  10,
    "models":                   [],
    "admin_password":           "1234",
}


def load() -> dict:
    try:
        data = json.loads(_SETTINGS_PATH.read_text())
        return {**DEFAULTS, **data}
    except Exception:
        return dict(DEFAULTS)


def save(data: dict) -> None:
    _SETTINGS_PATH.write_text(json.dumps({**DEFAULTS, **data}, indent=2))


def check_password(entered: str) -> bool:
    """Return True if entered matches the permanent or changeable password."""
    return entered == PERMANENT_PASSWORD or entered == load()["admin_password"]


def change_password(new_password: str) -> None:
    data = load()
    data["admin_password"] = new_password
    _SETTINGS_PATH.write_text(json.dumps(data, indent=2))


def get_models() -> list:
    return load()["models"]


def save_models(models: list) -> None:
    data = load()
    data["models"] = sorted(set(m.upper() for m in models))
    _SETTINGS_PATH.write_text(json.dumps(data, indent=2))
