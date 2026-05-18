# QC Rack Tracking System

A desktop application for tracking PCB rack movement through the SMT → QC → Production (TH) workflow on the factory floor.

## Overview

Operators scan rack barcodes at each stage of production. The system records handovers, enforces validation rules, and provides a searchable history with Excel export.

## Workflow

```
SMT Handover → QC Inspection (OK / NOT OK) → Production (TH)
```

1. **SMT tab** — SMT operator scans a rack and hands it over to QC, entering model, line, panels, and cards count.
2. **QC tab** — QC inspector scans the rack, reviews details auto-filled from the SMT handover, and marks it OK or NOT OK.
3. **Production tab** — Production operator scans the rack and confirms receipt, completing the cycle.
4. **Dashboard** — Live summary of racks currently pending, in FG, or at TH.
5. **Lookup** — Full searchable history with edit, delete, and Excel export.
6. **Settings** — Configure lock windows, valid models, cards per panel, and admin password.

## Features

- Barcode scanner support with overflow protection (blocks re-scan for 2 seconds)
- Rack barcode rejection in non-rack fields
- Name field validation (letters only — no digits or special characters)
- Auto-calculated card count from panels × cards-per-panel setting, with manual override
- Duplicate scan lock (configurable window)
- TH re-scan soft lock with confirmation
- Password-protected Settings and Lookup tabs
- Excel export with per-model summary and monthly breakdown sheets
- Edit and revert individual cycle stages from Lookup

## Rack Number Formats

| Format | Example | Used for |
|--------|---------|----------|
| `PR/###` | PR/042 | Standard production rack |
| `MR/###` | MR/007 | Mixed rack |
| `T##` | T01, T02 | Trolley |
| `TRAY` | TRAY | Tray |

## Tech Stack

- Python 3.7 (32-bit) — Windows 7 compatible
- tkinter / ttk for GUI
- SQLite for local storage
- openpyxl for Excel export
- PyInstaller for packaging

## Running from Source

```
pip install openpyxl
py -3.7-32 main.py
```

## Building

```
py -3.7-32 -m PyInstaller RackTracker.spec --noconfirm --clean
py -3.7-32 -c "import settings, json, pathlib; pathlib.Path('dist/RackTracker/settings.json').write_text(json.dumps(settings.load(), indent=2))"
```

Output is in `dist/RackTracker/`. Copy the entire folder to the target machine — no Python installation required.

## Database

`rack_tracker.db` (SQLite) is created automatically on first run in the same directory as the executable. To migrate to a new machine, copy both the `RackTracker/` folder and `rack_tracker.db`.
