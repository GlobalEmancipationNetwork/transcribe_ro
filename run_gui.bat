@echo off
REM Launcher script for Transcribe RO GUI (Windows)

cd /d "%~dp0"

echo =========================================
echo    Transcribe RO - GUI Launcher
echo =========================================
echo.

REM Check if virtual environment exists
if exist "venv\Scripts\activate.bat" (
    echo [OK] Virtual environment found
    call venv\Scripts\activate.bat
    echo [OK] Virtual environment activated
) else (
    echo [INFO] No virtual environment found
    echo        Using system Python
)

echo.
echo Starting Transcribe RO GUI...
echo.

REM Run the GUI application
python transcribe_ro_gui.py

REM Check if there was an error
if errorlevel 1 (
    echo.
    echo [WARNING] Application exited with an error
    echo.
    pause
)
