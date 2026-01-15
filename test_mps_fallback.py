#!/usr/bin/env python3
"""
Test script for MPS fallback functionality.
This verifies that the NaN detection and CPU fallback mechanisms are properly implemented.
"""

import os
import sys

def test_environment_variables():
    """Test that MPS environment variables are set."""
    print("="*80)
    print("TEST 1: Environment Variables")
    print("="*80)
    
    # Import transcribe_ro to trigger environment variable setting
    import transcribe_ro
    
    expected_vars = {
        'PYTORCH_ENABLE_MPS_FALLBACK': '1',
        'PYTORCH_MPS_HIGH_WATERMARK_RATIO': '0.0'
    }
    
    all_pass = True
    for var, expected_value in expected_vars.items():
        actual_value = os.environ.get(var)
        status = "✓ PASS" if actual_value == expected_value else "✗ FAIL"
        print(f"{status}: {var} = {actual_value} (expected: {expected_value})")
        if actual_value != expected_value:
            all_pass = False
    
    print()
    return all_pass

def test_nan_detection():
    """Test the NaN error detection logic."""
    print("="*80)
    print("TEST 2: NaN Error Detection")
    print("="*80)
    
    from transcribe_ro import AudioTranscriber
    
    transcriber = AudioTranscriber(model_name="tiny", device="cpu", verbose=False)
    
    test_cases = [
        ("Error during transcription: Expected parameter logits (Tensor of shape (1, 51865)) of distribution Categorical(logits: torch.Size([1, 51865])) to satisfy the constraint IndependentConstraint(Real(), 1), but found invalid values: tensor([[nan, nan, nan, ..., nan, nan, nan]], device='mps:0')", True),
        ("Error: NaN value detected in tensor", True),
        ("Error: Invalid values found in tensor", True),
        ("Normal error message about constraints", False),
        ("Connection timeout", False),
    ]
    
    all_pass = True
    for error_msg, should_detect in test_cases:
        detected = transcriber._detect_nan_error(error_msg)
        status = "✓ PASS" if detected == should_detect else "✗ FAIL"
        print(f"{status}: '{error_msg[:60]}...' -> detected={detected} (expected={should_detect})")
        if detected != should_detect:
            all_pass = False
    
    print()
    return all_pass

def test_cli_help():
    """Test that --force-cpu flag is in CLI help."""
    print("="*80)
    print("TEST 3: CLI Help for --force-cpu Flag")
    print("="*80)
    
    import subprocess
    
    try:
        result = subprocess.run(
            [sys.executable, "transcribe_ro.py", "--help"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        help_text = result.stdout
        
        if "--force-cpu" in help_text:
            print("✓ PASS: --force-cpu flag found in CLI help")
            lines = help_text.split('\n')
            matching_lines = [line for line in lines if 'force-cpu' in line]
            if matching_lines:
                print(f"Help text snippet: {matching_lines[0].strip()}")
            print()
            return True
        else:
            print("✗ FAIL: --force-cpu flag NOT found in CLI help")
            print()
            return False
            
    except Exception as e:
        print(f"✗ FAIL: Error running CLI help: {e}")
        print()
        return False

def test_gui_force_cpu_variable():
    """Test that GUI has force_cpu variable."""
    print("="*80)
    print("TEST 4: GUI Force CPU Variable")
    print("="*80)
    
    try:
        # Check if the GUI file has force_cpu variable
        with open("transcribe_ro_gui.py", "r") as f:
            gui_content = f.read()
        
        checks = {
            "force_cpu variable declared": "self.force_cpu" in gui_content,
            "force_cpu BooleanVar": "tk.BooleanVar" in gui_content and "self.force_cpu" in gui_content,
            "force_cpu checkbox": "ttk.Checkbutton" in gui_content and "force_cpu" in gui_content.lower(),
            "device_to_use logic": "device_to_use = 'cpu' if self.force_cpu.get()" in gui_content,
        }
        
        all_pass = True
        for check_name, passed in checks.items():
            status = "✓ PASS" if passed else "✗ FAIL"
            print(f"{status}: {check_name}")
            if not passed:
                all_pass = False
        
        print()
        return all_pass
        
    except Exception as e:
        print(f"✗ FAIL: Error checking GUI file: {e}")
        print()
        return False

def test_device_warnings():
    """Test that device detection includes MPS warnings."""
    print("="*80)
    print("TEST 5: MPS Device Warnings")
    print("="*80)
    
    try:
        with open("transcribe_ro.py", "r") as f:
            cli_content = f.read()
        
        checks = {
            "MPS warning in device_info": "'warning': 'MPS may encounter numerical instability" in cli_content,
            "NaN detection in transcribe_audio": "def _detect_nan_error" in cli_content,
            "CPU fallback logic": "Automatically falling back to CPU" in cli_content,
            "Fallback success message": "CPU FALLBACK SUCCESSFUL" in cli_content,
        }
        
        all_pass = True
        for check_name, passed in checks.items():
            status = "✓ PASS" if passed else "✗ FAIL"
            print(f"{status}: {check_name}")
            if not passed:
                all_pass = False
        
        print()
        return all_pass
        
    except Exception as e:
        print(f"✗ FAIL: Error checking CLI file: {e}")
        print()
        return False

def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("MPS FALLBACK FUNCTIONALITY TEST SUITE")
    print("="*80 + "\n")
    
    tests = [
        ("Environment Variables", test_environment_variables),
        ("NaN Detection Logic", test_nan_detection),
        ("CLI --force-cpu Flag", test_cli_help),
        ("GUI Force CPU Option", test_gui_force_cpu_variable),
        ("MPS Warnings", test_device_warnings),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results.append((test_name, passed))
        except Exception as e:
            print(f"✗ FAIL: {test_name} - Exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    total = len(results)
    passed_count = sum(1 for _, passed in results if passed)
    
    print()
    print(f"Total: {passed_count}/{total} tests passed")
    
    if passed_count == total:
        print("\n🎉 ALL TESTS PASSED! MPS fallback functionality is properly implemented.")
        return 0
    else:
        print(f"\n⚠️  {total - passed_count} test(s) failed. Please review the implementation.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
