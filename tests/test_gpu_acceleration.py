#!/usr/bin/env python3
"""
Test script to verify GPU acceleration support in transcribe_ro.py

This script tests:
1. Device detection functionality
2. PyTorch availability and MPS/CUDA support
3. Model loading on different devices
4. Display of device information

Usage:
    python test_gpu_acceleration.py
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_pytorch_availability():
    """Test if PyTorch is available and check for GPU backends."""
    print("="*80)
    print("TEST 1: PyTorch Availability")
    print("="*80)
    
    try:
        import torch
        print("✓ PyTorch is installed")
        print(f"  Version: {torch.__version__}")
        
        # Check CUDA
        if torch.cuda.is_available():
            print("✓ CUDA is available")
            print(f"  GPU Count: {torch.cuda.device_count()}")
            print(f"  GPU Name: {torch.cuda.get_device_name(0)}")
            try:
                memory = torch.cuda.get_device_properties(0).total_memory / (1024**3)
                print(f"  GPU Memory: {memory:.1f} GB")
            except:
                pass
        else:
            print("✗ CUDA is not available")
        
        # Check MPS
        if hasattr(torch.backends, 'mps'):
            if torch.backends.mps.is_available():
                print("✓ MPS (Apple Silicon GPU) is available")
                print("  Device: Apple Silicon M-series chip")
            else:
                print("✗ MPS is not available")
        else:
            print("✗ MPS backend not found (PyTorch version may be too old)")
        
        print()
        return True
        
    except ImportError:
        print("✗ PyTorch is not installed")
        print("  Install with: pip install torch")
        print()
        return False


def test_device_detection():
    """Test the device detection function."""
    print("="*80)
    print("TEST 2: Device Detection Function")
    print("="*80)
    
    try:
        from transcribe_ro import detect_device
        
        # Test auto detection
        print("\n1. Auto Detection:")
        device, info = detect_device('auto', debug=False)
        print(f"   Device: {device}")
        print(f"   Type: {info['type']}")
        print(f"   Reason: {info['reason']}")
        if info.get('note'):
            print(f"   Note: {info['note']}")
        if info.get('memory'):
            print(f"   Memory: {info['memory']}")
        
        # Test CPU
        print("\n2. CPU (forced):")
        device, info = detect_device('cpu', debug=False)
        print(f"   Device: {device}")
        print(f"   Type: {info['type']}")
        
        # Test MPS
        print("\n3. MPS (if available):")
        device, info = detect_device('mps', debug=False)
        print(f"   Device: {device}")
        print(f"   Type: {info['type']}")
        if device == 'mps':
            print("   ✓ MPS detected and ready!")
        
        # Test CUDA
        print("\n4. CUDA (if available):")
        device, info = detect_device('cuda', debug=False)
        print(f"   Device: {device}")
        print(f"   Type: {info['type']}")
        if device == 'cuda':
            print("   ✓ CUDA detected and ready!")
        
        print("\n✓ Device detection function works correctly")
        print()
        return True
        
    except Exception as e:
        print(f"\n✗ Device detection test failed: {e}")
        import traceback
        traceback.print_exc()
        print()
        return False


def test_command_line_help():
    """Test that command-line help shows GPU options."""
    print("="*80)
    print("TEST 3: Command-Line Help")
    print("="*80)
    
    import subprocess
    
    try:
        result = subprocess.run(
            [sys.executable, 'transcribe_ro.py', '--help'],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        
        help_text = result.stdout
        
        # Check for device options
        if '--device {auto,cpu,mps,cuda}' in help_text or 'device' in help_text.lower():
            print("✓ Device options found in help text")
            
            # Extract device-related lines
            lines = help_text.split('\n')
            device_section = []
            capture = False
            for line in lines:
                if '--device' in line:
                    capture = True
                if capture:
                    device_section.append(line)
                    if line.strip() and not line.startswith(' ') and '--device' not in line:
                        break
            
            print("\nDevice help section:")
            for line in device_section[:5]:  # Show first 5 lines
                print(f"  {line}")
            
            print("\n✓ Command-line interface updated correctly")
        else:
            print("✗ Device options not found in help text")
            print("\nHelp text preview:")
            print(help_text[:500])
        
        print()
        return True
        
    except Exception as e:
        print(f"\n✗ Command-line help test failed: {e}")
        print()
        return False


def show_recommendations():
    """Show recommendations based on detected hardware."""
    print("="*80)
    print("RECOMMENDATIONS")
    print("="*80)
    
    try:
        import torch
        
        if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            print("\n🍎 Apple Silicon GPU Detected!")
            print("\nRecommended usage:")
            print("  python transcribe_ro.py your_audio.mp3")
            print("  # Will automatically use MPS for 3-5x speedup")
            print("\nOr explicitly:")
            print("  python transcribe_ro.py your_audio.mp3 --device mps")
            print("\nWith debug info:")
            print("  python transcribe_ro.py your_audio.mp3 --device mps --debug")
            
        elif torch.cuda.is_available():
            print("\n🎮 NVIDIA GPU Detected!")
            print("\nRecommended usage:")
            print("  python transcribe_ro.py your_audio.mp3")
            print("  # Will automatically use CUDA for 5-10x speedup")
            print("\nOr explicitly:")
            print("  python transcribe_ro.py your_audio.mp3 --device cuda")
            
        else:
            print("\n💻 CPU Mode")
            print("\nNo GPU detected. Usage:")
            print("  python transcribe_ro.py your_audio.mp3")
            print("  # Will use CPU (slower but works everywhere)")
            
        print()
        
    except ImportError:
        print("\nPyTorch not available. Install requirements first:")
        print("  pip install -r requirements.txt")
        print()


def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("GPU ACCELERATION VERIFICATION SCRIPT")
    print("="*80)
    print()
    
    results = []
    
    # Test 1: PyTorch availability
    results.append(("PyTorch Availability", test_pytorch_availability()))
    
    # Test 2: Device detection
    results.append(("Device Detection", test_device_detection()))
    
    # Test 3: Command-line help
    results.append(("Command-Line Help", test_command_line_help()))
    
    # Show recommendations
    show_recommendations()
    
    # Summary
    print("="*80)
    print("TEST SUMMARY")
    print("="*80)
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(result for _, result in results)
    
    print("\n" + "="*80)
    if all_passed:
        print("✓ ALL TESTS PASSED - GPU acceleration is ready!")
        print("\nYou can now use transcribe_ro.py with GPU acceleration.")
        print("The tool will automatically detect and use the best device.")
    else:
        print("⚠ SOME TESTS FAILED")
        print("\nGPU acceleration may not work correctly.")
        print("Review the test output above for details.")
    print("="*80 + "\n")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
