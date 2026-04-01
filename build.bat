@echo off
:: Build a standalone Windows .exe using PyInstaller
:: Requirements: pip install pyinstaller PyQt6

echo Installing dependencies...
pip install PyQt6 pyinstaller

echo.
echo Building executable...
pyinstaller ^
    --onefile ^
    --windowed ^
    --name "RackTracker" ^
    --add-data "." ^
    main.py

echo.
echo Done. Executable is in the dist\ folder.
pause
