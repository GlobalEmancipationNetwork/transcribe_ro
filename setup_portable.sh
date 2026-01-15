#!/bin/bash
# Portable Setup Script for Transcribe RO (Linux/macOS)
# This script sets up the tool to run from a flash drive

set -e

echo "================================================================================"
echo "TRANSCRIBE RO - Portable Setup for Linux/macOS"
echo "================================================================================"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "[1/4] Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed!"
    echo "Please install Python 3.8+ using your package manager:"
    echo "  macOS: brew install python3"
    echo "  Ubuntu/Debian: sudo apt install python3 python3-venv python3-pip"
    echo "  Fedora: sudo dnf install python3 python3-pip"
    exit 1
fi
python3 --version
echo ""

echo "[2/4] Checking FFmpeg..."
if ! command -v ffmpeg &> /dev/null; then
    echo "WARNING: FFmpeg not found!"
    echo "Please install FFmpeg:"
    echo "  macOS: brew install ffmpeg"
    echo "  Ubuntu/Debian: sudo apt install ffmpeg"
    echo "  Fedora: sudo dnf install ffmpeg"
    echo ""
    read -p "Continue setup anyway? (y/n): " continue
    if [ "$continue" != "y" ] && [ "$continue" != "Y" ]; then
        exit 1
    fi
else
    echo "FFmpeg found!"
fi
echo ""

echo "[3/4] Creating virtual environment..."
if [ -d "venv" ]; then
    echo "Virtual environment already exists. Skipping..."
else
    python3 -m venv venv
    echo "Virtual environment created!"
fi
echo ""

echo "[4/4] Installing dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo ""

echo "================================================================================"
echo "SETUP COMPLETED SUCCESSFULLY!"
echo "================================================================================"
echo ""
echo "To use the tool, run: ./run_transcribe.sh your_audio_file.mp3"
echo "Or manually: source venv/bin/activate && python transcribe_ro.py audio.mp3"
echo ""
echo "TIP: On first use, the Whisper model will be downloaded (requires internet)."
echo "     After that, transcription can work offline (translation needs internet)."
echo ""
