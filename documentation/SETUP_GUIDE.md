# Transcribe RO - Setup Guide

## Introduction

**Transcribe RO** is a powerful audio transcription application designed to convert speech to text with advanced features including speaker diarization (identifying different speakers). This tool leverages state-of-the-art machine learning models to provide accurate transcriptions, making it ideal for interviews, meetings, podcasts, and other audio content that requires professional-grade text conversion.

This guide will walk you through the complete installation and setup process for your operating system. Follow the instructions specific to your platform (Windows, Mac, or Linux) to get started.

---

## Windows Setup

### Step 1: Install Python

Python 3.10 or higher is required for this application.

1. Download the latest Python installer from https://www.python.org/downloads/
2. Run the installer
3. **Important:** Check the box labeled **"Add Python to PATH"** during installation
4. Complete the installation
5. Verify the installation by opening Command Prompt and running:
   ```cmd
   python --version
   ```

### Step 2: Install Git

Git is required to clone the repository and manage updates.

1. Download Git from https://git-scm.com/download/win
2. Run the installer and follow the default installation options
3. Verify the installation:
   ```cmd
   git --version
   ```

### Step 3: Install FFmpeg

FFmpeg is essential for audio processing. You can install it using either method:

**Option A: Using winget (Recommended)**
```cmd
winget install FFmpeg
```

**Option B: Manual Installation**
1. Download FFmpeg from https://ffmpeg.org/download.html
2. Extract the downloaded archive to `C:\ffmpeg`
3. Add `C:\ffmpeg\bin` to your system PATH:
   - Open System Properties → Environment Variables
   - Edit the "Path" variable under System variables
   - Add a new entry: `C:\ffmpeg\bin`
   - Click OK to save

**Verify FFmpeg installation:**
```cmd
ffmpeg -version
```

### Step 4: Clone the Repository

Open Command Prompt or PowerShell and run:
```cmd
git clone https://github.com/GlobalEmancipationNetwork/transcribe_ro.git
cd transcribe_ro
```

### Step 5: Create Virtual Environment

Create an isolated Python environment for the application:
```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

You should see `(.venv)` appear at the beginning of your command prompt, indicating the virtual environment is active.

### Step 6: Install Dependencies

With the virtual environment activated, install the required Python packages:
```cmd
pip install -r requirements.txt
```

### Step 7: Fix torchcodec Incompatibility (Windows-Specific)

Due to a known compatibility issue on Windows, run these commands:
```cmd
pip install pyannote.audio
pip uninstall torchcodec -y
pip install hf_xet
```

### Step 8: Run the Application

Ensure your virtual environment is activated, then launch the application using either method:

**Method 1: Direct Python execution**
```cmd
python transcribe_ro_gui.py
```

**Method 2: Using the batch file**
```cmd
.\run_gui.bat
```

### Troubleshooting

**Issue: "The system cannot find the file specified"**
- **Cause:** FFmpeg is not installed or not in your system PATH
- **Solution:** Reinstall FFmpeg following Step 3 above, ensuring it's properly added to PATH

**Issue: "torchcodec/AudioDecoder incompatibility"**
- **Cause:** Incompatible version of torchcodec installed
- **Solution:** Run `pip uninstall torchcodec -y` and restart the application

**Issue: Speaker diarization not working**
- **Cause:** Missing or invalid HuggingFace token
- **Solution:** Ensure you have a valid HuggingFace token configured for accessing pyannote.audio models

### Updating the Application

When updates are available, run these commands from the transcribe_ro directory:
```cmd
git pull origin main
pip install -r requirements.txt --upgrade
pip uninstall torchcodec -y
```

---

## Mac Setup

### Step 1: Install Python

Python 3.10 or higher is required for this application.

**Option A: Using Homebrew (Recommended)**
```bash
brew install python
```

**Option B: Direct Download**
1. Download from https://www.python.org/downloads/
2. Run the installer and follow the instructions

**Verify installation:**
```bash
python3 --version
```

### Step 2: Install Git

**Option A: Using Homebrew (Recommended)**
```bash
brew install git
```

**Option B: Using Xcode Command Line Tools**
```bash
xcode-select --install
```

**Verify installation:**
```bash
git --version
```

### Step 3: Install FFmpeg

FFmpeg is essential for audio processing:
```bash
brew install ffmpeg
```

**Verify installation:**
```bash
ffmpeg -version
```

### Step 4: Clone the Repository

Open Terminal and run:
```bash
git clone https://github.com/GlobalEmancipationNetwork/transcribe_ro.git
cd transcribe_ro
```

### Step 5: Create Virtual Environment

Create an isolated Python environment for the application:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

You should see `(.venv)` appear at the beginning of your terminal prompt, indicating the virtual environment is active.

### Step 6: Install Dependencies

With the virtual environment activated, install the required Python packages:
```bash
pip install -r requirements.txt
```

### Step 7: Run the Application

Ensure your virtual environment is activated, then launch the application:
```bash
python transcribe_ro_gui.py
```

### Troubleshooting

**Issue: Speaker diarization not working**
- **Cause:** Missing or invalid HuggingFace token
- **Solution:** Ensure you have a valid HuggingFace token configured for accessing pyannote.audio models

**Issue: FFmpeg not found**
- **Cause:** FFmpeg not properly installed
- **Solution:** Reinstall using `brew install ffmpeg`

**Issue: Permission denied errors**
- **Cause:** Insufficient permissions
- **Solution:** Ensure you have proper read/write permissions in the installation directory

### Updating the Application

When updates are available, run these commands from the transcribe_ro directory:
```bash
git pull origin main
pip install -r requirements.txt --upgrade
```

---

## Linux Setup

### Step 1: Install Python

Python 3.10 or higher is required for this application.

**For Ubuntu/Debian-based distributions:**
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv
```

**For Fedora/RHEL-based distributions:**
```bash
sudo dnf install python3 python3-pip
```

**For Arch Linux:**
```bash
sudo pacman -S python python-pip
```

**Verify installation:**
```bash
python3 --version
```

### Step 2: Install Git

**For Ubuntu/Debian-based distributions:**
```bash
sudo apt install git
```

**For Fedora/RHEL-based distributions:**
```bash
sudo dnf install git
```

**For Arch Linux:**
```bash
sudo pacman -S git
```

**Verify installation:**
```bash
git --version
```

### Step 3: Install FFmpeg

FFmpeg is essential for audio processing.

**For Ubuntu/Debian-based distributions:**
```bash
sudo apt install ffmpeg
```

**For Fedora/RHEL-based distributions:**
```bash
sudo dnf install ffmpeg
```

**For Arch Linux:**
```bash
sudo pacman -S ffmpeg
```

**Verify installation:**
```bash
ffmpeg -version
```

### Step 4: Clone the Repository

Open your terminal and run:
```bash
git clone https://github.com/GlobalEmancipationNetwork/transcribe_ro.git
cd transcribe_ro
```

### Step 5: Create Virtual Environment

Create an isolated Python environment for the application:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

You should see `(.venv)` appear at the beginning of your terminal prompt, indicating the virtual environment is active.

### Step 6: Install Dependencies

With the virtual environment activated, install the required Python packages:
```bash
pip install -r requirements.txt
```

### Step 7: Run the Application

Ensure your virtual environment is activated, then launch the application:
```bash
python transcribe_ro_gui.py
```

### Troubleshooting

**Issue: Speaker diarization not working**
- **Cause:** Missing or invalid HuggingFace token
- **Solution:** Ensure you have a valid HuggingFace token configured for accessing pyannote.audio models

**Issue: FFmpeg not found**
- **Cause:** FFmpeg not properly installed
- **Solution:** Reinstall FFmpeg using your package manager as shown in Step 3

**Issue: Permission denied errors**
- **Cause:** Insufficient permissions
- **Solution:** Ensure you have proper read/write permissions in the installation directory. You may need to adjust ownership: `sudo chown -R $USER:$USER ~/transcribe_ro`

**Issue: Missing system dependencies**
- **Cause:** Some Python packages require system libraries
- **Solution:** Install development tools:
  - Ubuntu/Debian: `sudo apt install build-essential python3-dev`
  - Fedora/RHEL: `sudo dnf groupinstall "Development Tools"`
  - Arch: `sudo pacman -S base-devel`

### Updating the Application

When updates are available, run these commands from the transcribe_ro directory:
```bash
git pull origin main
pip install -r requirements.txt --upgrade
```

---

## Additional Notes

- Always ensure your virtual environment is activated before running the application or installing packages
- For optimal performance, use a computer with a dedicated GPU for faster transcription processing
- Keep your HuggingFace token secure and do not share it publicly
- If you encounter any issues not covered in the troubleshooting sections, please check the project's GitHub issues page or create a new issue with details about your problem

---

**Need Help?** Visit the project repository at https://github.com/GlobalEmancipationNetwork/transcribe_ro for additional documentation and community support.
