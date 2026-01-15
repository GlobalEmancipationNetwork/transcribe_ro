@echo off
REM Portable Setup Script for Transcribe RO (Windows)
REM This script sets up the tool to run from a flash drive

echo ================================================================================
echo TRANSCRIBE RO - Portable Setup for Windows
echo ================================================================================
echo.

REM Get the directory where this script is located
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

echo [1/4] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH!
    echo Please install Python 3.8+ from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)
python --version
echo.

echo [2/4] Checking FFmpeg...
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo WARNING: FFmpeg not found in PATH!
    echo Please download FFmpeg from https://ffmpeg.org/download.html
    echo and either:
    echo   1. Add it to your system PATH, or
    echo   2. Copy ffmpeg.exe to this folder: %SCRIPT_DIR%
    echo.
    set /p continue="Continue setup anyway? (y/n): "
    if /i not "%continue%"=="y" exit /b 1
) else (
    echo FFmpeg found!
)
echo.

echo [3/4] Creating virtual environment...
if exist venv (
    echo Virtual environment already exists. Skipping...
) else (
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment!
        pause
        exit /b 1
    )
    echo Virtual environment created!
)
echo.

echo [4/4] Installing dependencies...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies!
    pause
    exit /b 1
)
echo.

echo ================================================================================
echo SETUP COMPLETED SUCCESSFULLY!
echo ================================================================================
echo.
echo To use the tool, run: run_transcribe.bat your_audio_file.mp3
echo Or manually: venv\Scripts\activate.bat && python transcribe_ro.py audio.mp3
echo.
echo TIP: On first use, the Whisper model will be downloaded (requires internet).
echo      After that, transcription can work offline (translation needs internet).
echo.
pause
