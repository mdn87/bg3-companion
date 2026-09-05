@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\pythonw.exe" (
    start "" ".venv\Scripts\pythonw.exe" -m bg3_helper panel
) else (
    python -m bg3_helper panel
)
