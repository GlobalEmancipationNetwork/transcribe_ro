# Transcribe RO - Audio Transcription and Translation Tool

A powerful CLI and GUI tool for transcribing audio files in any language and translating them to Romanian. Uses OpenAI Whisper for automatic language detection and transcription.

## Features

- 🎤 **Audio Transcription**: Transcribe audio/video files using OpenAI Whisper
- 🌍 **Multi-language Support**: Automatic language detection and translation
- 🇷🇴 **Romanian Translation**: Online (Google) and offline (MarianMT) translation
- 👥 **Speaker Diarization**: Identify multiple speakers using pyannote.audio
- 🖥️ **GUI Application**: User-friendly graphical interface
- 🚀 **GPU Acceleration**: Support for CUDA (NVIDIA) and MPS (Apple Silicon)
- ⚙️ **Configurable**: TOML-based configuration for easy customization

## Installation

### 1. Install PyTorch (Required First)

PyTorch must be installed separately based on your system:

#### CUDA 12.1 (NVIDIA GPU - recommended for CUDA 12.0+)
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

#### CUDA 11.8 (NVIDIA GPU - older drivers)
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

#### CPU Only
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
```

#### macOS (Apple Silicon MPS or Intel)
```bash
pip install torch torchvision torchaudio
```

### 2. Install Transcribe RO

#### Basic Installation
```bash
pip install -e .
```

#### With All Optional Features
```bash
pip install -e ".[full]"
```

#### Individual Optional Features
```bash
# GUI support
pip install -e ".[gui]"

# Speaker diarization
pip install -e ".[diarization]"

# Development tools
pip install -e ".[dev]"
```

### 3. Verify Installation

Check device detection:
```bash
python device_manager.py
```

## Configuration

### config.toml

The `config.toml` file controls runtime behavior. Key settings:

#### Device Settings
```toml
[device]
# Device preference order (system will try each in order)
preference_order = ["cuda", "mps", "cpu"]

# Force a specific device (set to "auto" for automatic selection)
force_device = "auto"

# Enable MPS fallback for unsupported operations (Apple Silicon)
mps_fallback_enabled = true
```

#### Precision Settings
```toml
[precision]
# Options: "fp32" (default), "fp16" (faster), "bf16" (requires Ampere+)
default = "fp32"

# Enable automatic mixed precision
auto_mixed_precision = false
```

#### Whisper Settings
```toml
[whisper]
# Model size: "tiny", "base", "small", "medium", "large", "large-v2", "large-v3"
default_model = "base"
```

### Customizing Configuration

1. Copy `config.toml` to customize:
   ```bash
   cp config.toml ~/.config/transcribe_ro/config.toml
   ```

2. Edit settings as needed:
   ```bash
   nano ~/.config/transcribe_ro/config.toml
   ```

3. For GPU preference, modify the preference order:
   ```toml
   # Prefer MPS over CUDA (unusual, but possible)
   preference_order = ["mps", "cuda", "cpu"]
   
   # Force CPU only
   force_device = "cpu"
   ```

## Using the Device Manager

The `device_manager.py` module provides automatic device selection:

### Simple Usage

```python
from device_manager import get_device

# Automatically select the best device
device = get_device()  # Returns "cuda", "mps", or "cpu"

# Use with your model
model = whisper.load_model("base").to(device)
```

### Get torch.device Object

```python
from device_manager import get_torch_device

# Get torch.device directly
device = get_torch_device()
tensor = torch.zeros(10, device=device)
```

### Force a Specific Device

```python
from device_manager import get_device

# Force CPU even if GPU is available
device = get_device(force="cpu")

# Force CUDA (will fall back to CPU if unavailable)
device = get_device(force="cuda")
```

### Get Detailed Device Info

```python
from device_manager import get_device_info

info = get_device_info()
print(f"Using: {info['device_name']}")
print(f"Memory: {info.get('memory_gb', 'N/A')} GB")
```

### Advanced Usage with DeviceManager Class

```python
from device_manager import DeviceManager

# Create manager with custom config
dm = DeviceManager(config_path="/path/to/config.toml", debug=True)

# Get device with full info
device, info = dm.get_best_device()

# Get precision dtype
dtype = dm.get_dtype()  # Returns torch.float32, torch.float16, etc.
```

## Integration Example

Here's how to integrate the device manager into existing code:

### Before (Manual Device Detection)
```python
import torch

if torch.cuda.is_available():
    device = "cuda"
elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
    device = "mps"
else:
    device = "cpu"

model = whisper.load_model("base").to(device)
```

### After (Using Device Manager)
```python
from device_manager import get_device
import whisper

device = get_device()  # Handles all detection, validation, and logging
model = whisper.load_model("base").to(device)
```

## CLI Usage

```bash
# Basic transcription
python transcribe_ro.py audio.mp3

# Specify device
python transcribe_ro.py audio.mp3 --device cuda
python transcribe_ro.py audio.mp3 --device mps
python transcribe_ro.py audio.mp3 --device cpu

# With speaker diarization
python transcribe_ro.py audio.mp3 --diarize --speakers 2

# Debug mode
python transcribe_ro.py audio.mp3 --debug
```

## GUI Usage

```bash
python transcribe_ro_gui.py
```

## Troubleshooting

### PyTorch Falls Back to CPU

1. Run device diagnostics:
   ```bash
   python device_manager.py --debug
   ```

2. Verify PyTorch CUDA installation:
   ```python
   import torch
   print(f"CUDA available: {torch.cuda.is_available()}")
   print(f"CUDA version: {torch.version.cuda}")
   ```

3. Reinstall PyTorch with CUDA:
   ```bash
   pip uninstall torch torchvision torchaudio
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
   ```

### MPS Issues on Apple Silicon

1. Ensure macOS 12.3+ and compatible PyTorch version
2. Set environment variables (done automatically by device_manager):
   ```bash
   export PYTORCH_ENABLE_MPS_FALLBACK=1
   export PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0
   ```

3. Force CPU if MPS is unstable:
   ```toml
   # In config.toml
   [device]
   force_device = "cpu"
   ```

### Speaker Diarization Not Working

1. Install pyannote.audio:
   ```bash
   pip install pyannote.audio
   ```

2. Get HuggingFace token from https://huggingface.co/settings/tokens

3. Accept model terms at:
   - https://huggingface.co/pyannote/segmentation-3.0
   - https://huggingface.co/pyannote/speaker-diarization-3.1

4. Set token in config.toml or environment:
   ```toml
   [diarization]
   hf_token = "your_token_here"
   ```

## License

MIT License
