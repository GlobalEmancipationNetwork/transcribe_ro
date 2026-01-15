#!/bin/bash
# Launcher script for Transcribe RO GUI (Linux/macOS)

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "==========================================="
echo "   Transcribe RO - GUI Launcher"
echo "==========================================="
echo ""

# Check if virtual environment exists
if [ -d "venv" ]; then
    echo "✓ Virtual environment found"
    
    # Activate virtual environment
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
        echo "✓ Virtual environment activated"
    else
        echo "⚠️  Warning: Could not activate virtual environment"
        echo "   Trying to run with system Python..."
    fi
else
    echo "ℹ️  No virtual environment found"
    echo "   Using system Python"
fi

echo ""
echo "Starting Transcribe RO GUI..."
echo ""

# Run the GUI application
python3 transcribe_ro_gui.py

# Check exit status
if [ $? -ne 0 ]; then
    echo ""
    echo "⚠️  Application exited with an error"
    echo ""
    read -p "Press Enter to close..."
fi
