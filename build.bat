@echo off
echo ============================================================
echo  RackTracker Build  (Python 3.7 32-bit, folder mode)
echo ============================================================
echo.

echo [0/2] Locating Python 3.7 32-bit...
py -3.7-32 --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python 3.7 32-bit not found via Windows Launcher.
    echo        Install Python 3.7.9 32-bit from python.org ^(python-3.7.9.exe^)
    echo        and ensure the Python Launcher ^(py.exe^) is available in PATH.
    pause
    exit /b 1
)
py -3.7-32 --version

echo.
echo [1/2] Installing / updating dependencies...
py -3.7-32 -m pip install openpyxl "pyinstaller==5.13.2"
if %errorlevel% neq 0 (
    echo ERROR: pip install failed.
    pause
    exit /b 1
)

echo.
echo [2/2] Building with PyInstaller...
py -3.7-32 -m PyInstaller RackTracker.spec --noconfirm --clean
if %errorlevel% neq 0 (
    echo ERROR: PyInstaller build failed.
    pause
    exit /b 1
)

echo.
echo [3/3] Writing settings.json with current models into dist...
py -3.7-32 -c "import settings, json, pathlib; pathlib.Path('dist/RackTracker/settings.json').write_text(json.dumps(settings.load(), indent=2))"
if %errorlevel% neq 0 (
    echo WARNING: Could not write settings.json to dist.
)

echo.
echo ============================================================
echo  Done!  Distributable folder: dist\RackTracker\
echo  Run it with:  dist\RackTracker\RackTracker.exe
echo ============================================================
pause
