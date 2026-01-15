#!/bin/bash
# Example commands for using Transcribe RO
# This file demonstrates various use cases

echo "Transcribe RO - Example Commands"
echo "================================"
echo ""
echo "NOTE: Replace 'audio.mp3' with your actual audio file"
echo ""

# Activate virtual environment
source venv/bin/activate 2>/dev/null || echo "Run setup first: ./setup_portable.sh"

echo "1. Basic transcription with translation to Romanian:"
echo "   python transcribe_ro.py audio.mp3"
echo ""

echo "2. Fast transcription (tiny model):"
echo "   python transcribe_ro.py audio.mp3 --model tiny"
echo ""

echo "3. High accuracy transcription (medium model):"
echo "   python transcribe_ro.py audio.mp3 --model medium"
echo ""

echo "4. Transcribe without translation:"
echo "   python transcribe_ro.py audio.mp3 --no-translate"
echo ""

echo "5. Export as JSON:"
echo "   python transcribe_ro.py audio.mp3 --format json"
echo ""

echo "6. Generate SRT subtitle file:"
echo "   python transcribe_ro.py audio.mp3 --format srt"
echo ""

echo "7. Generate VTT subtitle file:"
echo "   python transcribe_ro.py audio.mp3 --format vtt"
echo ""

echo "8. Custom output file:"
echo "   python transcribe_ro.py audio.mp3 --output my_transcript.txt"
echo ""

echo "9. No timestamps in output:"
echo "   python transcribe_ro.py audio.mp3 --no-timestamps"
echo ""

echo "10. Use GPU for faster processing (if available):"
echo "    python transcribe_ro.py audio.mp3 --device cuda"
echo ""

echo "11. Combine multiple options:"
echo "    python transcribe_ro.py audio.mp3 --model small --format json --output result.json"
echo ""
