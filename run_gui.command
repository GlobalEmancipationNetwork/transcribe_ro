#!/bin/bash
# macOS launcher script for Transcribe RO GUI
# Double-click this file to launch the GUI on macOS

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

clear

echo "==========================================="
echo "   Transcribe RO - GUI Launcher (macOS)"
echo "==========================================="
echo ""

# Check if virtual environment exists
if [ -d "venv" ]; then
    echo "✓ Virtual environment found"
    source venv/bin/activate
    echo "✓ Virtual environment activated"
else
    echo "ℹ️  No virtual environment found, using system Python"
fi

echo ""
echo "Starting Transcribe RO GUI..."
echo ""

# Run the GUI application
python3 transcribe_ro_gui.py

# Keep terminal open if there was an error
if [ $? -ne 0 ]; then
    echo ""
    echo "⚠️  Application exited with an error"
    echo ""
    read -p "Press Enter to close..."
fi
