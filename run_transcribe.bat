@echo off
REM Run Transcribe RO (Windows)
REM This script activates the virtual environment and runs the transcription tool

REM Get the directory where this script is located
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

REM Check if virtual environment exists
if not exist venv (
    echo ERROR: Virtual environment not found!
    echo Please run setup_portable.bat first.
    pause
    exit /b 1
)

REM Activate virtual environment and run the tool
call venv\Scripts\activate.bat
python transcribe_ro.py %*

REM Keep window open if there was an error
if errorlevel 1 pause
