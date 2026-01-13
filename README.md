# 🎙️ Transcribe RO

A portable CLI tool for transcribing audio recordings in any language and translating them to Romanian. Built with OpenAI Whisper for automatic language detection and accurate transcription of 99+ languages.

## 🆕 What's New in v1.2.0

- **🎬 Video File Support**: Process MP4, AVI, MOV, MKV and other video formats
- **📦 Batch Processing**: Process entire directories with `--directory` option
- **🎤 Speaker Diarization**: Identify and label speakers with `--speakers` option
- **⏱️ Enhanced Timestamps**: Timestamps now included in both original AND translated outputs
- **🔄 Model Preloading**: Faster subsequent runs with automatic model downloading
- **🎯 Improved Default**: Changed default model from 'base' to 'small' for better accuracy

## ✨ Features

- **🖥️ User-Friendly GUI**: Graphical interface with file browser, language selection, and two-panel results display
- **💻 Command-Line Interface**: Powerful CLI for advanced users and automation
- **🌍 Multi-language Support**: Automatically detects and transcribes audio in 99+ languages
- **🇷🇴 Romanian Translation**: Translates transcriptions to Romanian automatically with timestamps
- **⚡ GPU Acceleration**: Supports Apple Silicon (M1/M2/M3) and NVIDIA CUDA for 3-10x faster transcription
- **🍎 Apple Silicon Optimized**: FP32 optimization eliminates FP16 warnings on M-series chips
- **🛡️ Automatic Error Recovery**: Detects MPS NaN errors and automatically falls back to CPU for reliable transcription
- **📁 Multiple Audio & Video Formats**: Supports MP3, WAV, M4A, MP4, AVI, MOV, MKV, and more
- **🎬 Video File Support**: Extract audio from video files automatically
- **⏱️ Timestamp Support**: Includes detailed timestamps for each segment in both original and translated outputs
- **📄 Multiple Output Formats**: Export as TXT, JSON, SRT, or VTT
- **📦 Batch Processing**: Process entire directories of audio/video files at once
- **🎤 Speaker Diarization**: Identify and label different speakers in recordings
- **💾 Portable**: Designed to run from a flash drive with minimal setup
- **🚀 Easy to Use**: Simple interfaces for both beginners and advanced users
- **🔧 Flexible**: Multiple model sizes for different accuracy/speed tradeoffs
- **🔄 Model Preloading**: Automatically downloads models on first use for faster subsequent runs

## 📋 Requirements

### System Requirements
- Python 3.8 or higher
- FFmpeg (for audio processing)
- At least 1GB free disk space (for model downloads)
- 4GB RAM minimum (8GB recommended for larger models)

### Operating Systems
- ✅ Windows 10/11
- ✅ macOS 10.15+
- ✅ Linux (Ubuntu, Debian, Fedora, etc.)

## 🚀 Quick Start

### Option 1: Standard Installation

1. **Clone or download this repository**:
   ```bash
   git clone https://github.com/yourusername/transcribe_ro.git
   cd transcribe_ro
   ```

2. **Install FFmpeg** (if not already installed):
   
   **Windows**:
   - Download from [ffmpeg.org](https://ffmpeg.org/download.html)
   - Add to PATH or place in the same folder as the script
   
   **macOS**:
   ```bash
   brew install ffmpeg
   ```
   
   **Linux**:
   ```bash
   sudo apt update
   sudo apt install ffmpeg  # Ubuntu/Debian
   sudo dnf install ffmpeg  # Fedora
   ```

3. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   
   # Activate on Windows
   venv\Scripts\activate
   
   # Activate on macOS/Linux
   source venv/bin/activate
   ```

4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

5. **Run your first transcription**:
   ```bash
   python transcribe_ro.py your_audio_file.mp3
   ```

### Option 2: Portable Flash Drive Setup

See the [Portable Setup Guide](#-portable-flash-drive-setup) below for detailed instructions on creating a portable version.

## 📖 Usage

### 🖥️ GUI Application (Recommended for Beginners)

For a user-friendly graphical interface, use the GUI version:

**Launch the GUI**:
```bash
# Linux/macOS
./run_gui.sh

# Windows
run_gui.bat

# macOS (double-click)
run_gui.command
```

Or run directly with Python:
```bash
python transcribe_ro_gui.py
```

**GUI Features**:
- 📁 **Easy File Selection**: Browse and select audio files with a file picker
- 🌍 **Language Selection**: Choose source language from a list (Romanian default)
- ⚙️ **Model Settings**: Select model size and device (CPU/GPU)
- 📊 **Two-Panel Display**: 
  - Left panel: Original transcript in source language
  - Right panel: Romanian translation
- 💾 **Copy & Save**: Copy to clipboard or save to file with one click
- 📈 **Progress Tracking**: Real-time progress bar and status updates
- 🖼️ **Resizable Window**: Adjust window and panel sizes to your preference

**Special Cases**:
- If audio is already in Romanian, only the transcript is shown (no translation panel)
- Translation is handled automatically based on detected language

### 💻 Command-Line Interface (CLI)

For advanced users and automation, use the CLI version:

### Basic Commands

**Transcribe an audio file**:
```bash
python transcribe_ro.py audio.mp3
```

**Transcribe without translation** (keep original language):
```bash
python transcribe_ro.py audio.mp3 --no-translate
```

**Use a specific model** (tiny, base, small, medium, large):
```bash
python transcribe_ro.py audio.mp3 --model medium
```

**Use GPU acceleration** (automatic detection):
```bash
python transcribe_ro.py audio.mp3
# Automatically uses Apple Silicon GPU (MPS) or NVIDIA GPU (CUDA) if available
```

**Force specific device**:
```bash
python transcribe_ro.py audio.mp3 --device mps   # Apple Silicon
python transcribe_ro.py audio.mp3 --device cuda  # NVIDIA GPU
python transcribe_ro.py audio.mp3 --device cpu   # Force CPU
```

**Specify output file**:
```bash
python transcribe_ro.py audio.mp3 --output my_transcription.txt
```

**Export as JSON**:
```bash
python transcribe_ro.py audio.mp3 --format json
```

**Generate subtitle files** (SRT or VTT):
```bash
python transcribe_ro.py audio.mp3 --format srt
python transcribe_ro.py audio.mp3 --format vtt
```

**Remove timestamps from output**:
```bash
python transcribe_ro.py audio.mp3 --no-timestamps
```

### 🎬 Video File Support

Transcribe RO now supports video files! The audio will be automatically extracted from video files.

**Supported video formats**: MP4, AVI, MOV, MKV, FLV, WMV, WEBM, MPEG, MPG

**Example**:
```bash
# Transcribe a video file
python transcribe_ro.py video.mp4

# Generate subtitles from video
python transcribe_ro.py video.mp4 --format srt

# Transcribe video without translation
python transcribe_ro.py video.mp4 --no-translate
```

### 📦 Batch Directory Processing

Process multiple audio/video files at once by specifying a directory instead of a single file.

**Example**:
```bash
# Process all audio/video files in a directory
python transcribe_ro.py --directory /path/to/media/files

# Batch process with specific format
python transcribe_ro.py --directory ./recordings --format srt

# Batch process without translation
python transcribe_ro.py --directory ./recordings --no-translate

# Batch process with specific model
python transcribe_ro.py --directory ./recordings --model medium
```

**Features**:
- Automatically finds all supported audio/video files in the directory
- Creates separate output files for each input file
- Shows progress for each file
- Provides summary of successful and failed files
- Continues processing even if individual files fail

### 🎤 Speaker Diarization

Identify and label different speakers in your recordings! This feature requires the `pyannote.audio` library and a HuggingFace token.

**Setup**:
1. Install pyannote.audio: `pip install pyannote.audio`
2. Get a HuggingFace token at https://huggingface.co/settings/tokens
3. Accept terms at https://huggingface.co/pyannote/speaker-diarization
4. Set environment variable: `export HF_TOKEN=your_token_here`

**Example**:
```bash
# Transcribe with two speakers
python transcribe_ro.py interview.mp3 --speakers "John,Mary"

# Speaker diarization with subtitles
python transcribe_ro.py interview.mp4 --speakers "Host,Guest" --format srt

# Batch process with speaker labels
python transcribe_ro.py --directory ./interviews --speakers "Interviewer,Interviewee"
```

**Output Format**:
- Speaker labels are included in timestamps: `[00:00:00 -> 00:00:05] [John] Hello, how are you?`
- Works with all output formats (TXT, JSON, SRT, VTT)
- Speaker labels are preserved in both original and translated outputs

**Note**: Speaker diarization works best with:
- Clear audio recordings
- Distinct speaker voices
- Two speakers (as specified)
- Good audio quality without background noise

### Command-Line Options

```
usage: transcribe_ro.py [-h] [-o OUTPUT] [-m {tiny,base,small,medium,large}]
                        [-f {txt,json,srt,vtt}] [--no-translate]
                        [--no-timestamps] [--device {auto,cpu,mps,cuda}]
                        [--force-cpu] [--translation-mode {auto,online,offline}]
                        [--debug] [-d DIRECTORY] [--speakers SPEAKERS] [--version]
                        [audio_file]

positional arguments:
  audio_file            Path to audio/video file (MP3, WAV, M4A, MP4, AVI, MOV, etc.)
                        Optional if --directory is specified

optional arguments:
  -h, --help            Show this help message and exit
  -o OUTPUT, --output OUTPUT
                        Output file path (default: <audio_file>_transcription.txt)
                        Note: When translation is enabled, TWO files are created:
                        - Original: <filename>_transcription.<format>
                        - Translated: <filename>_translated_ro.<format>
  -m {tiny,base,small,medium,large}, --model {tiny,base,small,medium,large}
                        Whisper model size (default: small)
  -f {txt,json,srt,vtt}, --format {txt,json,srt,vtt}
                        Output format (default: txt)
  --no-translate        Skip translation to Romanian (only transcribe)
                        Note: Only ONE file created when this flag is used
  --no-timestamps       Exclude timestamps from output (txt format only)
  --device {auto,cpu,mps,cuda}
                        Device to run on (default: auto - automatically detects best device)
                        Options:
                        - auto: Automatically detect and use the best available device
                        - cpu: Force CPU usage
                        - mps: Use Apple Silicon GPU (M1/M2/M3)
                        - cuda: Use NVIDIA GPU
  --force-cpu           Force CPU usage, bypassing GPU acceleration
  --translation-mode {auto,online,offline}
                        Translation mode (default: auto)
  --debug               Enable detailed debug output for troubleshooting
  -d DIRECTORY, --directory DIRECTORY
                        Process all audio/video files in the specified directory (batch mode)
  --speakers SPEAKERS   Enable speaker diarization with two speaker names separated by comma
                        Example: --speakers "John,Mary"
                        Requires: pip install pyannote.audio and HF_TOKEN environment variable
  --version             Show program's version number and exit
```

### Model Selection Guide

Choose the right model for your needs:

| Model  | Size  | Speed      | Accuracy | Recommended For |
|--------|-------|------------|----------|-----------------|
| tiny   | ~75MB | Fastest    | Good     | Quick tests, previews |
| base   | ~150MB| Very Fast  | Better   | Fast processing |
| small  | ~500MB| Fast       | Great    | **Default** - balanced accuracy & speed |
| medium | ~1.5GB| Moderate   | Excellent| High accuracy needs |
| large  | ~3GB  | Slow       | Best     | Maximum accuracy |

**Recommendation**: Start with `small` (default). Downgrade to `base` for faster processing or upgrade to `medium` if accuracy is critical.

## ⚡ GPU Acceleration

Transcribe RO supports GPU acceleration for significantly faster transcription speeds!

### 🚀 Performance Benefits

| Device | Speed vs CPU | Notes |
|--------|--------------|-------|
| **Apple Silicon (MPS)** | 3-5x faster | M1/M2/M3 chips, FP32 optimized |
| **NVIDIA GPU (CUDA)** | 5-10x faster | Requires CUDA-capable GPU |
| **CPU** | Baseline | Works everywhere |

### 🍎 Apple Silicon (M1/M2/M3) Support

**Automatic Detection** (Recommended):
```bash
python transcribe_ro.py audio.mp3
# Automatically detects and uses Apple Silicon GPU
```

**Manual Selection**:
```bash
python transcribe_ro.py audio.mp3 --device mps
```

**Key Benefits**:
- ✅ **FP16 Warning Eliminated**: Automatically uses FP32 for optimal performance
- ✅ **3-5x Faster**: Significant speed improvement over CPU
- ✅ **No Additional Setup**: Works out of the box on M1/M2/M3 Macs
- ✅ **Efficient Memory Usage**: Leverages unified memory architecture

**Example Output**:
```
================================================================================
🖥️  DEVICE CONFIGURATION
================================================================================
Selected Device: Apple Silicon GPU (MPS)
Reason: Apple Silicon GPU detected
Note: Using FP32 for optimal Apple Silicon performance
⚡ Apple Silicon GPU acceleration enabled - Expect 3-5x faster transcription
💡 Using FP32 for optimal Apple Silicon performance
✓ FP16 warning eliminated - MPS configured correctly
================================================================================
```

#### ⚠️ MPS NaN Error - Automatic Fallback

**Known Issue**: In some cases, Whisper on Apple Silicon GPUs may encounter numerical instability (NaN errors). This is a known upstream issue with certain chip variants (e.g., M3 MAX).

**Automatic Solution**: Transcribe RO now includes **transparent automatic CPU fallback**:

- ✅ **Automatic Detection**: NaN errors are detected instantly
- ✅ **Seamless Fallback**: Automatically retries on CPU without user intervention
- ✅ **Clear Messaging**: You'll see exactly what happened and that it's being fixed
- ✅ **No Data Loss**: Transcription completes successfully

**Manual Override**: If you want to skip GPU entirely:

```bash
# Force CPU mode (skips GPU attempt)
python transcribe_ro.py audio.mp3 --force-cpu

# Or in GUI: Check the "Force CPU" checkbox
```

**What You'll See** (if MPS encounters NaN error):
```
⚠️  MPS NaN ERROR DETECTED
This is a known issue with Whisper on Apple Silicon GPUs.
Automatically falling back to CPU for stable transcription...

Loading model on CPU device...
✓ Model successfully reloaded on CPU!
✓ CPU FALLBACK SUCCESSFUL!
Transcription completed using CPU after MPS encountered errors.
```

📖 **For more details**, see [MPS_NAN_FIX.md](MPS_NAN_FIX.md)

### 🎮 NVIDIA GPU (CUDA) Support

**Automatic Detection**:
```bash
python transcribe_ro.py audio.mp3
# Automatically detects and uses CUDA if available
```

**Manual Selection**:
```bash
python transcribe_ro.py audio.mp3 --device cuda
```

**Requirements**:
- CUDA-capable NVIDIA GPU
- PyTorch with CUDA support (usually auto-installed)

### 💻 CPU Mode

**Force CPU Usage** (useful for debugging):
```bash
python transcribe_ro.py audio.mp3 --device cpu
```

### 🔍 Device Selection Priority

When using `--device auto` (default), the tool automatically selects the best device in this order:

1. **CUDA** (NVIDIA GPU) - if available
2. **MPS** (Apple Silicon GPU) - if available  
3. **CPU** - fallback

### 💡 Troubleshooting GPU Issues

If you experience issues with GPU acceleration:

1. **Check PyTorch Installation**:
   ```bash
   python -c "import torch; print(f'MPS available: {torch.backends.mps.is_available()}')"
   python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
   ```

2. **View Device Detection Details**:
   ```bash
   python transcribe_ro.py audio.mp3 --debug
   ```

3. **Force CPU as Fallback**:
   ```bash
   python transcribe_ro.py audio.mp3 --device cpu
   ```

## 📂 Output Formats

### 🎯 Dual-File Output (When Translation is Enabled)

**Important**: When translation is performed, the tool creates **TWO separate files**:

1. **Original Transcription File**: `<filename>_transcription.<format>`
   - Contains the transcribed text in the detected language
   - Preserves the original language content

2. **Translated File**: `<filename>_translated_ro.<format>`
   - Contains the Romanian translation
   - Separate file for easy comparison and use

**Example**: For `audio.m4a`:
- Creates: `audio_transcription.txt` (original English text)
- Creates: `audio_translated_ro.txt` (Romanian translation)

This applies to **all output formats**: `txt`, `json`, `srt`, `vtt`

### TXT Format (Default)

**Original Transcription File** (`audio_transcription.txt`):
```
================================================================================
TRANSCRIPTION RESULTS (ORIGINAL LANGUAGE)
================================================================================

METADATA:
----------------------------------------
Source File: audio.mp3
Detected Language: en
Transcription Date: 2026-01-12T10:30:00
Model Used: base
Translation Applied: True

TRANSCRIPTION:
----------------------------------------
Hello, this is a test recording...

TIMESTAMPS:
----------------------------------------
[00:00:00 -> 00:00:05] Hello, this is a test recording
[00:00:06 -> 00:00:10] It demonstrates the transcription feature
```

**Translated File** (`audio_translated_ro.txt`):
```
================================================================================
ROMANIAN TRANSLATION
================================================================================

METADATA:
----------------------------------------
Source File: audio.mp3
Detected Language: en
File Type: romanian_translation
Original Language: en
Transcription Date: 2026-01-12T10:30:00
Model Used: base

TRANSLATED TEXT:
----------------------------------------
Bună, aceasta este o înregistrare de test...
```

### JSON Format
Creates two JSON files with structured data:
- `<filename>_transcription.json` - Original language data
- `<filename>_translated_ro.json` - Romanian translation data

Both contain metadata, text content, and detailed segment information.

### SRT/VTT Format
Creates two subtitle files:
- `<filename>_transcription.srt/vtt` - Original language subtitles
- `<filename>_translated_ro.srt/vtt` - Romanian translated subtitles

Standard subtitle formats with timestamps, perfect for video subtitling.

## 🎯 Use Cases

- **Conference Recordings**: Transcribe multilingual meetings and translate to Romanian
- **Interviews**: Convert interview recordings to searchable text with speaker identification
- **Lectures**: Create transcripts of educational content
- **Podcasts**: Generate transcripts for accessibility with speaker labels
- **Voice Notes**: Convert voice memos to text
- **Video Subtitles**: Generate subtitle files directly from video files
- **Legal/Medical**: Transcribe professional recordings (use larger models)
- **Batch Processing**: Transcribe entire folders of recordings efficiently
- **Video Content**: Extract and transcribe audio from video files for subtitles or documentation
- **Multi-Speaker Content**: Identify and label different speakers in conversations and interviews

## 💾 Portable Flash Drive Setup

This tool is designed to be portable and run directly from a USB flash drive without installing anything on the host computer.

### Creating a Portable Installation

#### Windows

1. **Prepare the Flash Drive**:
   - Use a USB drive with at least 8GB free space
   - Create a folder called `transcribe_ro`

2. **Install Portable Python**:
   - Download [Python Embedded Package](https://www.python.org/downloads/windows/)
   - Extract to `E:\transcribe_ro\python` (adjust drive letter)

3. **Copy FFmpeg**:
   - Download FFmpeg from [ffmpeg.org](https://ffmpeg.org/download.html)
   - Extract and copy `ffmpeg.exe` to `E:\transcribe_ro\`

4. **Copy Application Files**:
   - Copy `transcribe_ro.py`, `requirements.txt`, and `setup_portable.bat` to the flash drive

5. **Run Setup**:
   - Double-click `setup_portable.bat` to install dependencies

6. **Use the Tool**:
   ```cmd
   E:\transcribe_ro\run_transcribe.bat your_audio.mp3
   ```

#### Linux/macOS

1. **Prepare the Flash Drive**:
   ```bash
   cd /Volumes/YourUSB  # macOS
   # or
   cd /media/usb        # Linux
   
   mkdir transcribe_ro
   cd transcribe_ro
   ```

2. **Create Virtual Environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Make Launch Script**:
   Create `run.sh`:
   ```bash
   #!/bin/bash
   SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
   source "$SCRIPT_DIR/venv/bin/activate"
   python "$SCRIPT_DIR/transcribe_ro.py" "$@"
   ```
   
   Make executable:
   ```bash
   chmod +x run.sh
   ```

5. **Use the Tool**:
   ```bash
   ./run.sh your_audio.mp3
   ```

### Important Notes for Portable Use

- **First Run**: The first time you use a specific model, it will be downloaded (requires internet)
- **Model Cache**: Models are cached in the user's home directory, not on the flash drive
- **Offline Use**: After downloading models, the tool can work offline (except for translation)
- **Translation**: Google Translate requires internet connection. Use `--no-translate` for offline use

## 🔧 Troubleshooting

### Common Issues

**1. "FFmpeg not found" error**:
- Ensure FFmpeg is installed and in your system PATH
- Or place `ffmpeg.exe` (Windows) in the same folder as the script

**2. "Model download failed"**:
- Check your internet connection
- Ensure you have enough disk space
- Models are downloaded to `~/.cache/whisper/`

**3. "Out of memory" error**:
- Use a smaller model: `--model tiny` or `--model base`
- Close other applications
- Process shorter audio files

**4. Translation not working**:
- **USE DEBUG MODE**: `python transcribe_ro.py audio.mp3 --debug`
- Ensure internet connection is available
- Check that deep-translator is installed: `pip install deep-translator>=1.11.4`
- See DEBUG_MODE_GUIDE.md for detailed troubleshooting

**5. Slow processing**:
- Use a smaller model for faster processing
- Consider using GPU: `--device cuda` (requires CUDA setup)
- Trim long audio files

**6. Audio format not supported**:
- Convert to MP3 or WAV using online tools or FFmpeg
- Check file is not corrupted

### Debug Mode 🔍

When troubleshooting issues (especially translation problems), enable debug mode:

```bash
python transcribe_ro.py audio.mp3 --debug
```

**Debug mode shows:**
- ✅ Detailed step-by-step progress
- ✅ Language detection with confidence
- ✅ Translation decisions and reasons
- ✅ Text samples (first 200 characters)
- ✅ Retry attempts with timing
- ✅ Full error stack traces
- ✅ File paths and sizes
- ✅ Timing for each step

**See DEBUG_MODE_GUIDE.md for comprehensive troubleshooting guide.**

### Getting Help

If you encounter issues:
1. **Run with --debug flag first**: `python transcribe_ro.py audio.mp3 --debug`
2. Check the error message carefully
3. Review DEBUG_MODE_GUIDE.md for specific issues
4. Ensure all requirements are installed: `pip list`
5. Verify FFmpeg installation: `ffmpeg -version`
6. Try with a different audio file to isolate the issue
7. Use a smaller model to test: `--model tiny`

## 🤝 Contributing

Contributions are welcome! Feel free to:
- Report bugs
- Suggest new features
- Submit pull requests
- Improve documentation

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- [OpenAI Whisper](https://github.com/openai/whisper) - Robust speech recognition
- [FFmpeg](https://ffmpeg.org/) - Audio processing
- [googletrans](https://github.com/ssut/py-googletrans) - Translation services

## 📮 Contact

For questions, suggestions, or support, please open an issue on GitHub.

---

**Made with ❤️ for the Romanian community**
