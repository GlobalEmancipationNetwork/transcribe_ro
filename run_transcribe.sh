#!/bin/bash
# Run Transcribe RO (Linux/macOS)
# This script activates the virtual environment and runs the transcription tool

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "ERROR: Virtual environment not found!"
    echo "Please run ./setup_portable.sh first."
    exit 1
fi

# Activate virtual environment and run the tool
source venv/bin/activate
python transcribe_ro.py "$@"
