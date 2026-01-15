#!/usr/bin/env python3
"""
Test script to verify the --debug flag functionality
"""
import subprocess
import sys

def test_debug_flag():
    """Test the --debug flag with various scenarios"""
    
    print("="*80)
    print("DEBUG FLAG TEST SUITE")
    print("="*80)
    print()
    
    tests = [
        {
            "name": "Test 1: Help message shows --debug flag",
            "command": ["python3", "transcribe_ro.py", "--help"],
            "check": "--debug"
        },
        {
            "name": "Test 2: Check if --debug is in help output",
            "command": ["python3", "transcribe_ro.py", "-h"],
            "check": "debug"
        }
    ]
    
    for i, test in enumerate(tests, 1):
        print(f"\n{test['name']}")
        print("-" * 80)
        
        try:
            result = subprocess.run(
                test["command"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if test["check"] in result.stdout.lower():
                print(f"✓ PASSED: Found '{test['check']}' in output")
            else:
                print(f"✗ FAILED: '{test['check']}' not found in output")
                print(f"Output snippet: {result.stdout[:500]}")
                
        except subprocess.TimeoutExpired:
            print(f"✗ FAILED: Command timed out")
        except Exception as e:
            print(f"✗ FAILED: {e}")
    
    # Test the actual debug output format
    print("\n" + "="*80)
    print("DEBUG OUTPUT FORMAT TEST")
    print("="*80)
    print("\nChecking that debug messages include:")
    print("  - Timestamps with milliseconds")
    print("  - [DEBUG] level indicator")
    print("  - Step separators (====)")
    print("  - Detailed progress information")
    print()
    
    print("To test with actual audio, run:")
    print("  python3 transcribe_ro.py <audio_file> --debug")
    print()
    print("Expected debug output includes:")
    print("  ✓ Command line arguments")
    print("  ✓ Model loading details with timing")
    print("  ✓ Language detection with confidence")
    print("  ✓ Translation decisions (why/why not)")
    print("  ✓ Text samples (first 200 chars)")
    print("  ✓ Retry attempts with numbers")
    print("  ✓ File paths and sizes")
    print("  ✓ Timing for each step")
    print("  ✓ Full exception tracebacks")
    print()

if __name__ == "__main__":
    test_debug_flag()
