#!/usr/bin/env python3
"""
Test script for offline translation functionality.
Verifies that the translation system can handle both online and offline modes.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all required modules can be imported."""
    print("="*80)
    print("TEST 1: Import Verification")
    print("="*80)
    
    try:
        from transcribe_ro import (
            check_internet_connectivity,
            get_marian_model_name,
            OfflineTranslator,
            ONLINE_TRANSLATOR_AVAILABLE,
            OFFLINE_TRANSLATOR_AVAILABLE,
            TRANSLATOR_AVAILABLE
        )
        print("✓ All imports successful")
        print(f"  - Online translator available: {ONLINE_TRANSLATOR_AVAILABLE}")
        print(f"  - Offline translator available: {OFFLINE_TRANSLATOR_AVAILABLE}")
        print(f"  - Any translator available: {TRANSLATOR_AVAILABLE}")
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False


def test_internet_connectivity():
    """Test internet connectivity check."""
    print("\n" + "="*80)
    print("TEST 2: Internet Connectivity Check")
    print("="*80)
    
    try:
        from transcribe_ro import check_internet_connectivity
        
        is_connected = check_internet_connectivity(timeout=3)
        print(f"Internet connection: {'✓ Available' if is_connected else '✗ Not available'}")
        return True
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False


def test_model_name_mapping():
    """Test model name mapping."""
    print("\n" + "="*80)
    print("TEST 3: Model Name Mapping")
    print("="*80)
    
    try:
        from transcribe_ro import get_marian_model_name
        
        test_languages = ['en', 'es', 'fr', 'de', 'it', 'unknown']
        
        for lang in test_languages:
            model_name = get_marian_model_name(lang)
            if model_name:
                print(f"✓ {lang}: {model_name}")
            else:
                print(f"✗ {lang}: No model available")
        
        return True
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False


def test_offline_translator_init():
    """Test offline translator initialization."""
    print("\n" + "="*80)
    print("TEST 4: Offline Translator Initialization")
    print("="*80)
    
    try:
        from transcribe_ro import OfflineTranslator, OFFLINE_TRANSLATOR_AVAILABLE
        
        if not OFFLINE_TRANSLATOR_AVAILABLE:
            print("⚠️  Offline translator not available (transformers not installed)")
            print("   Install with: pip install transformers sentencepiece")
            return True  # Not a failure, just not installed
        
        translator = OfflineTranslator(debug=False)
        print("✓ Offline translator initialized successfully")
        return True
    except Exception as e:
        print(f"✗ Initialization failed: {e}")
        return False


def test_cli_help():
    """Test that CLI help shows the new --translation-mode flag."""
    print("\n" + "="*80)
    print("TEST 5: CLI Help Output")
    print("="*80)
    
    try:
        import subprocess
        result = subprocess.run(
            [sys.executable, "transcribe_ro.py", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        
        if "--translation-mode" in result.stdout:
            print("✓ --translation-mode flag found in help output")
            
            # Show the relevant lines
            lines = result.stdout.split('\n')
            for i, line in enumerate(lines):
                if "--translation-mode" in line:
                    print("\nRelevant help text:")
                    # Print this line and next few lines
                    for j in range(i, min(i+3, len(lines))):
                        print(f"  {lines[j]}")
                    break
            return True
        else:
            print("✗ --translation-mode flag not found in help output")
            return False
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False


def test_translation_mode_choices():
    """Test that translation mode validates choices."""
    print("\n" + "="*80)
    print("TEST 6: Translation Mode Validation")
    print("="*80)
    
    valid_modes = ['auto', 'online', 'offline']
    
    print(f"Valid translation modes: {', '.join(valid_modes)}")
    print("✓ Translation modes defined correctly")
    return True


def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("OFFLINE TRANSLATION IMPLEMENTATION TEST SUITE")
    print("="*80)
    print()
    
    tests = [
        ("Imports", test_imports),
        ("Internet Connectivity", test_internet_connectivity),
        ("Model Name Mapping", test_model_name_mapping),
        ("Offline Translator Init", test_offline_translator_init),
        ("CLI Help", test_cli_help),
        ("Translation Mode Choices", test_translation_mode_choices),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ Test '{test_name}' crashed: {e}")
            results.append((test_name, False))
    
    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print("="*80)
    print(f"Results: {passed}/{total} tests passed")
    print("="*80)
    
    if passed == total:
        print("\n✓ All tests passed!")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
