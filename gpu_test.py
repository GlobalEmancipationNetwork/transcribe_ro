#!/usr/bin/env python3
"""
GPU Detection and Testing Script
================================
Comprehensive diagnostic tool for PyTorch GPU/CUDA setup.
Helps troubleshoot why PyTorch might be falling back to CPU.
"""

import sys
import time
import platform
import subprocess
from typing import Optional, Dict, Any

# ============================================================================
# SECTION 1: CPU INFORMATION
# ============================================================================

def get_cpu_info() -> Dict[str, Any]:
    """Detect and return CPU information."""
    info = {
        "processor": platform.processor() or "Unknown",
        "machine": platform.machine(),
        "system": platform.system(),
        "python_version": platform.python_version(),
    }
    
    # Get number of CPU cores
    try:
        import multiprocessing
        info["cpu_count_logical"] = multiprocessing.cpu_count()
    except:
        info["cpu_count_logical"] = "Unknown"
    
    # Try to get more detailed CPU info based on OS
    system = platform.system()
    
    if system == "Linux":
        try:
            with open("/proc/cpuinfo", "r") as f:
                cpuinfo = f.read()
            for line in cpuinfo.split("\n"):
                if "model name" in line:
                    info["cpu_name"] = line.split(":")[1].strip()
                    break
            # Count physical cores
            physical_cores = len(set(
                line.split(":")[1].strip() 
                for line in cpuinfo.split("\n") 
                if "physical id" in line
            ))
            info["cpu_count_physical"] = physical_cores if physical_cores > 0 else "Unknown"
        except:
            pass
    
    elif system == "Darwin":  # macOS
        try:
            result = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                info["cpu_name"] = result.stdout.strip()
            
            # Check for Apple Silicon
            result = subprocess.run(
                ["sysctl", "-n", "hw.optional.arm64"],
                capture_output=True, text=True
            )
            info["is_apple_silicon"] = result.returncode == 0 and "1" in result.stdout
        except:
            pass
    
    elif system == "Windows":
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"
            )
            info["cpu_name"] = winreg.QueryValueEx(key, "ProcessorNameString")[0]
            winreg.CloseKey(key)
        except:
            try:
                result = subprocess.run(
                    ["wmic", "cpu", "get", "name"],
                    capture_output=True, text=True, shell=True
                )
                lines = [l.strip() for l in result.stdout.split("\n") if l.strip() and l.strip() != "Name"]
                if lines:
                    info["cpu_name"] = lines[0]
            except:
                pass
    
    return info


def print_cpu_info(info: Dict[str, Any]) -> None:
    """Display CPU information."""
    print("\n" + "=" * 60)
    print("🖥️  CPU INFORMATION")
    print("=" * 60)
    print(f"  System:           {info.get('system', 'Unknown')}")
    print(f"  Machine:          {info.get('machine', 'Unknown')}")
    print(f"  CPU Name:         {info.get('cpu_name', info.get('processor', 'Unknown'))}")
    print(f"  Logical Cores:    {info.get('cpu_count_logical', 'Unknown')}")
    if "cpu_count_physical" in info:
        print(f"  Physical Cores:   {info['cpu_count_physical']}")
    if info.get("is_apple_silicon"):
        print(f"  Apple Silicon:    ✅ Yes")
    print(f"  Python Version:   {info.get('python_version', 'Unknown')}")


# ============================================================================
# SECTION 2: GPU INFORMATION
# ============================================================================

def get_nvidia_smi_info() -> Optional[Dict[str, Any]]:
    """Get GPU info from nvidia-smi command."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,memory.free,memory.used,driver_version,cuda_version",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            gpus = []
            for line in lines:
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 6:
                    gpus.append({
                        "name": parts[0],
                        "memory_total_mb": parts[1],
                        "memory_free_mb": parts[2],
                        "memory_used_mb": parts[3],
                        "driver_version": parts[4],
                        "cuda_version": parts[5],
                    })
            return {"gpus": gpus, "available": True}
    except FileNotFoundError:
        return {"available": False, "error": "nvidia-smi not found"}
    except Exception as e:
        return {"available": False, "error": str(e)}
    return {"available": False, "error": "Unknown error"}


def print_nvidia_info(info: Dict[str, Any]) -> None:
    """Display NVIDIA GPU information from nvidia-smi."""
    print("\n" + "-" * 60)
    print("🎮 NVIDIA GPU (nvidia-smi)")
    print("-" * 60)
    
    if not info.get("available"):
        print(f"  ❌ nvidia-smi not available: {info.get('error', 'Unknown error')}")
        return
    
    for i, gpu in enumerate(info.get("gpus", [])):
        print(f"\n  GPU {i}:")
        print(f"    Name:           {gpu.get('name', 'Unknown')}")
        print(f"    Memory Total:   {gpu.get('memory_total_mb', 'Unknown')} MB")
        print(f"    Memory Free:    {gpu.get('memory_free_mb', 'Unknown')} MB")
        print(f"    Memory Used:    {gpu.get('memory_used_mb', 'Unknown')} MB")
        print(f"    Driver Version: {gpu.get('driver_version', 'Unknown')}")
        print(f"    CUDA Version:   {gpu.get('cuda_version', 'Unknown')}")


# ============================================================================
# SECTION 3: PYTORCH AND CUDA CHECK
# ============================================================================

def check_pytorch() -> Dict[str, Any]:
    """Check PyTorch installation and CUDA support."""
    info = {"installed": False}
    
    try:
        import torch
        info["installed"] = True
        info["version"] = torch.__version__
        info["cuda_available"] = torch.cuda.is_available()
        info["cuda_built"] = torch.backends.cuda.is_built() if hasattr(torch.backends.cuda, 'is_built') else "Unknown"
        
        if info["cuda_available"]:
            info["cuda_version"] = torch.version.cuda
            info["cudnn_version"] = torch.backends.cudnn.version() if torch.backends.cudnn.is_available() else None
            info["cudnn_enabled"] = torch.backends.cudnn.enabled
            info["device_count"] = torch.cuda.device_count()
            info["current_device"] = torch.cuda.current_device()
            info["device_name"] = torch.cuda.get_device_name(0)
            
            # Get GPU memory info
            try:
                info["gpu_memory_total"] = torch.cuda.get_device_properties(0).total_memory / (1024**3)
                info["gpu_memory_allocated"] = torch.cuda.memory_allocated(0) / (1024**3)
                info["gpu_memory_cached"] = torch.cuda.memory_reserved(0) / (1024**3)
            except:
                pass
            
            # Get compute capability
            try:
                props = torch.cuda.get_device_properties(0)
                info["compute_capability"] = f"{props.major}.{props.minor}"
                info["multi_processor_count"] = props.multi_processor_count
            except:
                pass
        
        # Check MPS (Apple Silicon)
        try:
            info["mps_available"] = torch.backends.mps.is_available()
            info["mps_built"] = torch.backends.mps.is_built()
        except:
            info["mps_available"] = False
            info["mps_built"] = False
        
    except ImportError as e:
        info["error"] = f"PyTorch not installed: {e}"
    except Exception as e:
        info["error"] = str(e)
    
    return info


def print_pytorch_info(info: Dict[str, Any]) -> None:
    """Display PyTorch and CUDA information."""
    print("\n" + "=" * 60)
    print("🔥 PYTORCH INFORMATION")
    print("=" * 60)
    
    if not info.get("installed"):
        print(f"  ❌ PyTorch not installed: {info.get('error', 'Unknown error')}")
        return
    
    print(f"  PyTorch Version:  {info.get('version', 'Unknown')}")
    print(f"  CUDA Built:       {'✅ Yes' if info.get('cuda_built') else '❌ No'}")
    print(f"  CUDA Available:   {'✅ Yes' if info.get('cuda_available') else '❌ No'}")
    
    if info.get("cuda_available"):
        print(f"\n  CUDA Details:")
        print(f"    CUDA Version:       {info.get('cuda_version', 'Unknown')}")
        print(f"    cuDNN Version:      {info.get('cudnn_version', 'Not available')}")
        print(f"    cuDNN Enabled:      {'✅ Yes' if info.get('cudnn_enabled') else '❌ No'}")
        print(f"    Device Count:       {info.get('device_count', 'Unknown')}")
        print(f"    Current Device:     {info.get('current_device', 'Unknown')}")
        print(f"    Device Name:        {info.get('device_name', 'Unknown')}")
        
        if "compute_capability" in info:
            print(f"    Compute Capability: {info['compute_capability']}")
        if "multi_processor_count" in info:
            print(f"    SM Count:           {info['multi_processor_count']}")
        
        if "gpu_memory_total" in info:
            print(f"\n  GPU Memory:")
            print(f"    Total:      {info['gpu_memory_total']:.2f} GB")
            print(f"    Allocated:  {info.get('gpu_memory_allocated', 0):.4f} GB")
            print(f"    Cached:     {info.get('gpu_memory_cached', 0):.4f} GB")
    
    # MPS (Apple Silicon) info
    if info.get("mps_built"):
        print(f"\n  Apple MPS (Metal):")
        print(f"    MPS Built:      {'✅ Yes' if info.get('mps_built') else '❌ No'}")
        print(f"    MPS Available:  {'✅ Yes' if info.get('mps_available') else '❌ No'}")


# ============================================================================
# SECTION 4: PERFORMANCE TEST
# ============================================================================

def run_inference_test(device: str, iterations: int = 100) -> Dict[str, Any]:
    """Run a simple neural network inference test."""
    import torch
    import torch.nn as nn
    
    # Define a simple CNN
    class SimpleCNN(nn.Module):
        def __init__(self):
            super().__init__()
            self.conv1 = nn.Conv2d(3, 32, 3, padding=1)
            self.conv2 = nn.Conv2d(32, 64, 3, padding=1)
            self.conv3 = nn.Conv2d(64, 128, 3, padding=1)
            self.pool = nn.MaxPool2d(2, 2)
            self.fc1 = nn.Linear(128 * 4 * 4, 512)
            self.fc2 = nn.Linear(512, 10)
            self.relu = nn.ReLU()
        
        def forward(self, x):
            x = self.pool(self.relu(self.conv1(x)))
            x = self.pool(self.relu(self.conv2(x)))
            x = self.pool(self.relu(self.conv3(x)))
            x = x.view(-1, 128 * 4 * 4)
            x = self.relu(self.fc1(x))
            x = self.fc2(x)
            return x
    
    result = {"device": device, "success": False}
    
    try:
        # Create model and move to device
        model = SimpleCNN()
        model = model.to(device)
        model.eval()
        
        # Create random input (batch of 16 images, 3 channels, 32x32)
        batch_size = 16
        input_tensor = torch.randn(batch_size, 3, 32, 32).to(device)
        
        # Warmup
        with torch.no_grad():
            for _ in range(10):
                _ = model(input_tensor)
        
        # Synchronize if CUDA
        if device.startswith("cuda"):
            torch.cuda.synchronize()
        
        # Timed inference
        start_time = time.perf_counter()
        with torch.no_grad():
            for _ in range(iterations):
                output = model(input_tensor)
        
        # Synchronize if CUDA
        if device.startswith("cuda"):
            torch.cuda.synchronize()
        
        end_time = time.perf_counter()
        
        total_time = end_time - start_time
        avg_time = total_time / iterations
        throughput = (iterations * batch_size) / total_time
        
        result.update({
            "success": True,
            "total_time_ms": total_time * 1000,
            "avg_time_ms": avg_time * 1000,
            "throughput_samples_per_sec": throughput,
            "iterations": iterations,
            "batch_size": batch_size,
        })
        
    except Exception as e:
        result["error"] = str(e)
    
    return result


def print_performance_comparison(results: Dict[str, Dict]) -> None:
    """Display performance comparison between devices."""
    print("\n" + "=" * 60)
    print("⚡ PERFORMANCE TEST RESULTS")
    print("=" * 60)
    print("  Test: SimpleCNN inference (batch=16, 32x32 RGB images)")
    print("  Iterations: 100")
    
    for device_name, result in results.items():
        print(f"\n  {device_name.upper()}:")
        if result.get("success"):
            print(f"    Total Time:   {result['total_time_ms']:.2f} ms")
            print(f"    Avg/Batch:    {result['avg_time_ms']:.4f} ms")
            print(f"    Throughput:   {result['throughput_samples_per_sec']:.1f} samples/sec")
        else:
            print(f"    ❌ Failed: {result.get('error', 'Unknown error')}")
    
    # Calculate speedup
    if "cpu" in results and results["cpu"].get("success"):
        cpu_time = results["cpu"]["avg_time_ms"]
        
        for device_name in ["cuda", "mps"]:
            if device_name in results and results[device_name].get("success"):
                device_time = results[device_name]["avg_time_ms"]
                speedup = cpu_time / device_time
                print(f"\n  📊 {device_name.upper()} Speedup vs CPU: {speedup:.2f}x")


# ============================================================================
# SECTION 5: DIAGNOSTIC SUGGESTIONS
# ============================================================================

def print_diagnostics(cpu_info: Dict, pytorch_info: Dict, nvidia_info: Dict) -> None:
    """Print diagnostic suggestions based on detected configuration."""
    print("\n" + "=" * 60)
    print("🔍 DIAGNOSTIC ANALYSIS & SUGGESTIONS")
    print("=" * 60)
    
    issues = []
    suggestions = []
    
    system = cpu_info.get("system", "")
    
    # Check if PyTorch is installed
    if not pytorch_info.get("installed"):
        issues.append("PyTorch is not installed")
        suggestions.append("Install PyTorch: pip install torch torchvision torchaudio")
        suggestions.append("For CUDA support, visit: https://pytorch.org/get-started/locally/")
    
    # Check CUDA availability
    elif not pytorch_info.get("cuda_available"):
        if system == "Darwin" and cpu_info.get("is_apple_silicon"):
            # Apple Silicon Mac
            if pytorch_info.get("mps_available"):
                print("  ✅ Apple Silicon detected with MPS support available")
                print("     Use device='mps' for GPU acceleration")
            else:
                issues.append("MPS not available on Apple Silicon")
                suggestions.append("Update PyTorch: pip install --upgrade torch torchvision torchaudio")
                suggestions.append("Ensure macOS 12.3+ is installed")
        
        elif system == "Darwin":
            # Intel Mac
            print("  ℹ️  Intel Mac detected - CUDA is not supported on macOS")
            suggestions.append("Consider using cloud GPU services (Google Colab, AWS, etc.)")
        
        elif nvidia_info.get("available"):
            # NVIDIA GPU detected but CUDA not available in PyTorch
            issues.append("NVIDIA GPU detected but PyTorch CUDA is not available")
            suggestions.append("You have a CPU-only version of PyTorch installed")
            suggestions.append("Reinstall PyTorch with CUDA support:")
            suggestions.append("  pip uninstall torch torchvision torchaudio")
            suggestions.append("  pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118")
            suggestions.append("  (Replace cu118 with your CUDA version: cu117, cu118, cu121, etc.)")
            
            # Check CUDA version compatibility
            if nvidia_info.get("gpus"):
                driver_cuda = nvidia_info["gpus"][0].get("cuda_version", "")
                suggestions.append(f"  Your driver supports CUDA {driver_cuda}")
        
        else:
            issues.append("No NVIDIA GPU detected")
            suggestions.append("Check if NVIDIA drivers are installed")
            if system == "Windows":
                suggestions.append("Download drivers from: https://www.nvidia.com/Download/index.aspx")
            elif system == "Linux":
                suggestions.append("Install NVIDIA drivers: sudo apt install nvidia-driver-xxx")
                suggestions.append("Check GPU with: lspci | grep -i nvidia")
    
    else:
        print("  ✅ CUDA is available and working!")
    
    # Print issues and suggestions
    if issues:
        print("\n  ⚠️  Issues Detected:")
        for issue in issues:
            print(f"     • {issue}")
    
    if suggestions:
        print("\n  💡 Suggestions:")
        for suggestion in suggestions:
            print(f"     • {suggestion}")
    
    # Additional tips
    print("\n  📝 General Tips:")
    print("     • Ensure PyTorch version matches your CUDA version")
    print("     • Run 'nvidia-smi' to check GPU status (NVIDIA only)")
    print("     • Check PyTorch CUDA: python -c \"import torch; print(torch.cuda.is_available())\"")
    print("     • For Apple Silicon: use device='mps' instead of 'cuda'")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    print("\n" + "=" * 60)
    print("   GPU DETECTION AND TESTING SCRIPT")
    print("   PyTorch CUDA/MPS Diagnostic Tool")
    print("=" * 60)
    
    # 1. Get CPU info
    cpu_info = get_cpu_info()
    print_cpu_info(cpu_info)
    
    # 2. Get NVIDIA GPU info (if available)
    nvidia_info = get_nvidia_smi_info()
    print_nvidia_info(nvidia_info)
    
    # 3. Check PyTorch
    pytorch_info = check_pytorch()
    print_pytorch_info(pytorch_info)
    
    # 4. Run performance tests
    if pytorch_info.get("installed"):
        import torch
        
        results = {}
        
        # CPU test
        print("\n  Running CPU inference test...")
        results["cpu"] = run_inference_test("cpu")
        
        # CUDA test
        if pytorch_info.get("cuda_available"):
            print("  Running CUDA inference test...")
            results["cuda"] = run_inference_test("cuda")
        
        # MPS test (Apple Silicon)
        if pytorch_info.get("mps_available"):
            print("  Running MPS inference test...")
            results["mps"] = run_inference_test("mps")
        
        print_performance_comparison(results)
    
    # 5. Print diagnostics
    print_diagnostics(cpu_info, pytorch_info, nvidia_info)
    
    print("\n" + "=" * 60)
    print("   Test Complete!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
