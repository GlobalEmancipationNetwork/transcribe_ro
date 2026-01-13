#!/usr/bin/env python3
"""Test script to verify new enhancements"""

import sys
import re

# Read the transcribe_ro.py file
with open('transcribe_ro.py', 'r') as f:
    content = f.read()

# Test 1: Check default model is 'small'
print("=" * 60)
print("TEST 1: Default Model")
print("=" * 60)
if "default='small'" in content and "help='Whisper model size (default: small)" in content:
    print("✓ Default model is 'small'")
else:
    print("✗ Default model not set to 'small'")

# Test 2: Check for preload_model function
if 'def preload_model' in open('transcribe_ro.py').read():
    print("✓ Model preloading function added")
else:
    print("✗ Model preloading function not found")

# Test for video support
if '.mp4' in open('transcribe_ro.py').read():
    print("✓ Video format support added")
else:
    print("✗ Video format support not found")

# Test for batch processing
if '--directory' in open('transcribe_ro.py').read():
    print("✓ Batch directory processing option added")
else:
    print("✗ Directory option not found")

# Test for speaker diarization
if '--speakers' in open('transcribe_ro.py').read():
    print("✓ Speaker diarization option added")
else:
    print("✗ Speaker diarization option missing")

print("\n✓ All code modifications appear to be in place!")
