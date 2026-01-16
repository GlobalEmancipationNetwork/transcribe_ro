#!/usr/bin/env python3
"""
Device Manager - Automatic Device Selection for PyTorch

This module provides a simple API for selecting the best available compute device
based on configuration preferences. It handles CUDA, MPS (Apple Silicon), and CPU
with graceful fallback.

Usage:
    from device_manager import get_device, DeviceManager
    
    # Simple usage - returns torch device string
    device = get_device()
    
    # Advanced usage with full info
    dm = DeviceManager()
    device, info = dm.get_best_device()
"""

import os
import sys
import logging
from pathlib import Path
from typing import Tuple, Dict, Any, Optional, List

# Setup module logger
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration from TOML file.
    
    Args:
        config_path: Path to config.toml. If None, searches in:
                    1. Current directory
                    2. Same directory as this module
                    3. User's home directory (~/.config/transcribe_ro/)
    
    Returns:
        dict: Configuration dictionary
    """
    try:
        import toml
    except ImportError:
        logger.warning("toml package not installed. Using default configuration.")
        logger.warning("Install with: pip install toml")
        return get_default_config()
    
    # Search paths for config file
    search_paths = [
        Path(config_path) if config_path else None,
        Path.cwd() / "config.toml",
        Path(__file__).parent / "config.toml",
        Path.home() / ".config" / "transcribe_ro" / "config.toml",
    ]
    
    for path in search_paths:
        if path and path.exists():
            try:
                config = toml.load(str(path))
                logger.debug(f"Loaded configuration from: {path}")
                return config
            except Exception as e:
                logger.warning(f"Failed to load config from {path}: {e}")
                continue
    
    logger.info("No config.toml found. Using default configuration.")
    return get_default_config()


def get_default_config() -> Dict[str, Any]:
    """Return default configuration."""
    return {
        "device": {
            "preference_order": ["cuda", "mps", "cpu"],
            "force_device": "auto",
            "mps_fallback_enabled": True,
            "mps_high_watermark_ratio": 0.0,
        },
        "precision": {
            "default": "fp32",
            "auto_mixed_precision": False,
        },
    }


class DeviceManager:
    """
    Manages device selection for PyTorch computations.
    
    Automatically detects and selects the best available device based on
    configuration preferences, with graceful fallback.
    """
    
    def __init__(self, config_path: Optional[str] = None, debug: bool = False):
        """
        Initialize the DeviceManager.
        
        Args:
            config_path: Optional path to config.toml
            debug: Enable debug logging
        """
        if debug:
            logger.setLevel(logging.DEBUG)
        
        self.config = load_config(config_path)
        self._setup_environment()
        self._torch = None
        self._device = None
        self._device_info = None
    
    def _setup_environment(self) -> None:
        """Setup environment variables based on configuration."""
        device_config = self.config.get("device", {})
        
        # MPS-specific environment variables
        if device_config.get("mps_fallback_enabled", True):
            os.environ['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'
        
        watermark = device_config.get("mps_high_watermark_ratio", 0.0)
        os.environ['PYTORCH_MPS_HIGH_WATERMARK_RATIO'] = str(watermark)
    
    @property
    def torch(self):
        """Lazy-load PyTorch."""
        if self._torch is None:
            try:
                import torch
                self._torch = torch
            except ImportError:
                logger.error("PyTorch not installed. Install with: pip install torch")
                raise ImportError("PyTorch is required but not installed")
        return self._torch
    
    def get_preference_order(self) -> List[str]:
        """Get device preference order from config."""
        return self.config.get("device", {}).get("preference_order", ["cuda", "mps", "cpu"])
    
    def get_forced_device(self) -> Optional[str]:
        """Get forced device from config, or None if auto."""
        forced = self.config.get("device", {}).get("force_device", "auto")
        return None if forced == "auto" else forced
    
    def get_precision(self) -> str:
        """Get default precision from config."""
        return self.config.get("precision", {}).get("default", "fp32")
    
    def is_cuda_available(self) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if CUDA is available and working.
        
        Returns:
            tuple: (is_available, device_info)
        """
        info = {"name": "cuda", "available": False}
        
        try:
            if not self.torch.cuda.is_available():
                info["reason"] = "CUDA not available (no GPU or drivers not installed)"
                return False, info
            
            # Get detailed CUDA info
            device_count = self.torch.cuda.device_count()
            info.update({
                "available": True,
                "device_count": device_count,
                "cuda_version": self.torch.version.cuda,
            })
            
            if device_count > 0:
                props = self.torch.cuda.get_device_properties(0)
                info.update({
                    "device_name": props.name,
                    "memory_gb": round(props.total_memory / (1024**3), 1),
                    "compute_capability": f"{props.major}.{props.minor}",
                })
            
            # Verify CUDA actually works with a simple operation
            test_tensor = self.torch.zeros(1, device="cuda")
            del test_tensor
            self.torch.cuda.empty_cache()
            
            logger.debug(f"CUDA available: {info['device_name']}, {info.get('memory_gb', 'N/A')} GB")
            return True, info
            
        except Exception as e:
            info["reason"] = f"CUDA check failed: {str(e)}"
            logger.debug(f"CUDA availability check failed: {e}")
            return False, info
    
    def is_mps_available(self) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if MPS (Apple Silicon) is available and working.
        
        Returns:
            tuple: (is_available, device_info)
        """
        info = {"name": "mps", "available": False}
        
        try:
            # Check if MPS backend exists and is available
            if not hasattr(self.torch.backends, 'mps'):
                info["reason"] = "MPS backend not available in this PyTorch version"
                return False, info
            
            if not self.torch.backends.mps.is_available():
                info["reason"] = "MPS not available (not Apple Silicon or unsupported macOS)"
                return False, info
            
            # Validate MPS actually works
            test_tensor = self.torch.zeros(1, device="mps")
            test_result = test_tensor + 1
            
            # Synchronize to ensure operation completed
            if hasattr(self.torch.mps, 'synchronize'):
                self.torch.mps.synchronize()
            
            # Check for NaN (common MPS issue)
            if self.torch.isnan(test_result).any():
                info["reason"] = "MPS returned NaN values during validation"
                logger.warning("MPS available but produces NaN values")
                return False, info
            
            del test_tensor, test_result
            
            info.update({
                "available": True,
                "device_name": "Apple Silicon GPU",
            })
            
            logger.debug("MPS (Apple Silicon) available and validated")
            return True, info
            
        except Exception as e:
            info["reason"] = f"MPS check failed: {str(e)}"
            logger.debug(f"MPS availability check failed: {e}")
            return False, info
    
    def get_cpu_info(self) -> Dict[str, Any]:
        """Get CPU device info."""
        import platform
        return {
            "name": "cpu",
            "available": True,
            "device_name": platform.processor() or "CPU",
            "reason": "CPU is always available",
        }
    
    def get_best_device(self, force: Optional[str] = None) -> Tuple[str, Dict[str, Any]]:
        """
        Detect and return the best available device.
        
        Args:
            force: Force a specific device (overrides config)
        
        Returns:
            tuple: (device_name, device_info)
                   device_name is one of: "cuda", "mps", "cpu"
        """
        # Check for forced device
        forced_device = force or self.get_forced_device()
        if forced_device:
            logger.info(f"Device forced to: {forced_device}")
            return self._validate_forced_device(forced_device)
        
        # Try devices in preference order
        preference_order = self.get_preference_order()
        logger.debug(f"Device preference order: {preference_order}")
        
        for device_type in preference_order:
            if device_type == "cuda":
                available, info = self.is_cuda_available()
                if available:
                    self._log_device_selection("cuda", info)
                    return "cuda", info
                    
            elif device_type == "mps":
                available, info = self.is_mps_available()
                if available:
                    self._log_device_selection("mps", info)
                    return "mps", info
                    
            elif device_type == "cpu":
                info = self.get_cpu_info()
                self._log_device_selection("cpu", info)
                return "cpu", info
        
        # Fallback to CPU if nothing else worked
        info = self.get_cpu_info()
        info["reason"] = "Fallback to CPU (no preferred device available)"
        self._log_device_selection("cpu", info)
        return "cpu", info
    
    def _validate_forced_device(self, device: str) -> Tuple[str, Dict[str, Any]]:
        """Validate and return forced device, with fallback to CPU if unavailable."""
        if device == "cuda":
            available, info = self.is_cuda_available()
            if available:
                self._log_device_selection("cuda", info)
                return "cuda", info
            logger.warning(f"Forced device 'cuda' not available: {info.get('reason')}")
            logger.warning("Falling back to CPU")
            
        elif device == "mps":
            available, info = self.is_mps_available()
            if available:
                self._log_device_selection("mps", info)
                return "mps", info
            logger.warning(f"Forced device 'mps' not available: {info.get('reason')}")
            logger.warning("Falling back to CPU")
            
        elif device == "cpu":
            info = self.get_cpu_info()
            self._log_device_selection("cpu", info)
            return "cpu", info
        
        # Fallback to CPU
        info = self.get_cpu_info()
        info["reason"] = f"Forced device '{device}' not available, using CPU"
        self._log_device_selection("cpu", info)
        return "cpu", info
    
    def _log_device_selection(self, device: str, info: Dict[str, Any]) -> None:
        """Log device selection."""
        device_name = info.get("device_name", device)
        
        if device == "cuda":
            memory = info.get("memory_gb", "N/A")
            cuda_ver = info.get("cuda_version", "N/A")
            logger.info(f"🚀 Using CUDA GPU: {device_name} ({memory} GB, CUDA {cuda_ver})")
        elif device == "mps":
            logger.info(f"🍎 Using MPS (Apple Silicon): {device_name}")
        else:
            logger.info(f"💻 Using CPU: {device_name}")
            logger.info("   Consider using GPU for faster transcription:")
            logger.info("   - NVIDIA GPU: Install CUDA-enabled PyTorch")
            logger.info("   - Apple Silicon: Ensure MPS is properly configured")
    
    def get_torch_device(self, force: Optional[str] = None):
        """
        Get torch.device object for the best available device.
        
        Args:
            force: Force a specific device
        
        Returns:
            torch.device: The selected device
        """
        device_name, info = self.get_best_device(force=force)
        self._device = device_name
        self._device_info = info
        return self.torch.device(device_name)
    
    def get_dtype(self):
        """
        Get the appropriate torch dtype based on precision config.
        
        Returns:
            torch.dtype: The precision dtype (float32, float16, or bfloat16)
        """
        precision = self.get_precision()
        dtype_map = {
            "fp32": self.torch.float32,
            "fp16": self.torch.float16,
            "bf16": self.torch.bfloat16,
        }
        return dtype_map.get(precision, self.torch.float32)


# =============================================================================
# Simple API Functions
# =============================================================================

# Global DeviceManager instance (lazy initialization)
_device_manager: Optional[DeviceManager] = None


def get_device_manager(config_path: Optional[str] = None, debug: bool = False) -> DeviceManager:
    """
    Get or create the global DeviceManager instance.
    
    Args:
        config_path: Optional path to config.toml
        debug: Enable debug logging
    
    Returns:
        DeviceManager: The global device manager instance
    """
    global _device_manager
    if _device_manager is None:
        _device_manager = DeviceManager(config_path=config_path, debug=debug)
    return _device_manager


def get_device(force: Optional[str] = None, config_path: Optional[str] = None) -> str:
    """
    Get the best available device name.
    
    This is the simplest API for device selection.
    
    Args:
        force: Force a specific device ("cuda", "mps", or "cpu")
        config_path: Optional path to config.toml
    
    Returns:
        str: Device name ("cuda", "mps", or "cpu")
    
    Example:
        >>> device = get_device()
        >>> model = model.to(device)
    """
    dm = get_device_manager(config_path=config_path)
    device, _ = dm.get_best_device(force=force)
    return device


def get_torch_device(force: Optional[str] = None, config_path: Optional[str] = None):
    """
    Get torch.device object for the best available device.
    
    Args:
        force: Force a specific device
        config_path: Optional path to config.toml
    
    Returns:
        torch.device: The selected device object
    
    Example:
        >>> device = get_torch_device()
        >>> tensor = torch.zeros(10, device=device)
    """
    dm = get_device_manager(config_path=config_path)
    return dm.get_torch_device(force=force)


def get_device_info(force: Optional[str] = None, config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Get detailed information about the selected device.
    
    Args:
        force: Force a specific device
        config_path: Optional path to config.toml
    
    Returns:
        dict: Device information including name, availability, and capabilities
    """
    dm = get_device_manager(config_path=config_path)
    _, info = dm.get_best_device(force=force)
    return info


# =============================================================================
# Main - Device Diagnostics
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Device Manager - Check available compute devices")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    parser.add_argument("--config", type=str, help="Path to config.toml")
    parser.add_argument("--force", choices=["cuda", "mps", "cpu"], help="Force specific device")
    args = parser.parse_args()
    
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    print("="*60)
    print("Device Manager - PyTorch Device Detection")
    print("="*60)
    
    dm = DeviceManager(config_path=args.config, debug=args.debug)
    
    print(f"\n📋 Configuration:")
    print(f"   Preference order: {dm.get_preference_order()}")
    print(f"   Forced device: {dm.get_forced_device() or 'auto'}")
    print(f"   Default precision: {dm.get_precision()}")
    
    print(f"\n🔍 Checking available devices...")
    
    # Check CUDA
    cuda_available, cuda_info = dm.is_cuda_available()
    print(f"\n   CUDA: {'✅ Available' if cuda_available else '❌ Not available'}")
    if cuda_available:
        print(f"         Device: {cuda_info.get('device_name')}")
        print(f"         Memory: {cuda_info.get('memory_gb')} GB")
        print(f"         CUDA Version: {cuda_info.get('cuda_version')}")
    else:
        print(f"         Reason: {cuda_info.get('reason', 'Unknown')}")
    
    # Check MPS
    mps_available, mps_info = dm.is_mps_available()
    print(f"\n   MPS:  {'✅ Available' if mps_available else '❌ Not available'}")
    if not mps_available:
        print(f"         Reason: {mps_info.get('reason', 'Unknown')}")
    
    # CPU always available
    print(f"\n   CPU:  ✅ Always available")
    
    print(f"\n🎯 Selected device:")
    device, info = dm.get_best_device(force=args.force)
    
    print(f"\n" + "="*60)
    print(f"Use in code: device = get_device()  # Returns: '{device}'")
    print("="*60)
