# Transcribe RO - Setup Guide

## Prerequisites

### 1. Install Python (3.10 or higher recommended)

**Windows:**
1. Download from https://www.python.org/downloads/
2. Run installer and **check "Add Python to PATH"**
3. Verify: `python --version`

**macOS:**
```bash
brew install python
```
Or download from https://www.python.org/downloads/

### 2. Install Git

**Windows:**
Download from https://git-scm.com/download/win

**macOS:**
```bash
brew install git
```
Or install Xcode Command Line Tools: `xcode-select --install`

### 3. Install FFmpeg

**Windows (using winget):**
```cmd
winget install FFmpeg
```

**Windows (manual):**
1. Download from https://ffmpeg.org/download.html
2. Extract to `C:\ffmpeg`
3. Add `C:\ffmpeg\bin` to your system PATH

**macOS:**
```bash
brew install ffmpeg
```

Verify installation: `ffmpeg -version`

---

## Installation

### 1. Clone the Repository
```bash
git clone https://github.com/GlobalEmancipationNetwork/transcribe_ro.git
cd transcribe_ro
```

### 2. Create Virtual Environment

**Windows:**
```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

**macOS/Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Windows Only - Fix torchcodec Incompatibility
```cmd
pip install pyannote.audio
pip uninstall torchcodec -y
pip install hf_xet
```
---

## Running the Application

Make sure your virtual environment is activated, then:

```bash
python transcribe_ro_gui.py
```

---

## Troubleshooting

### "The system cannot find the file specified" (Windows)
FFmpeg is not installed or not in PATH. See FFmpeg installation above.

### "torchcodec/AudioDecoder incompatibility"
Run: `pip uninstall torchcodec -y` and restart the application.

### Speaker diarization not working
Ensure you have a valid HuggingFace token configured for pyannote.audio models.

---

## Updating

```bash
git pull origin main
pip install -r requirements.txt --upgrade
# Windows only:
pip uninstall torchcodec -y
```
