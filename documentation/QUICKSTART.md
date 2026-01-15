# 🚀 Quick Start Guide - Transcribe RO

## For Beginners

This guide will help you get started with Transcribe RO in just a few minutes!

### Step 1: Check Requirements

Before you begin, make sure you have:
- ✅ Python 3.8 or newer installed
- ✅ Internet connection (for initial setup)
- ✅ An audio file to transcribe (MP3, WAV, etc.)

### Step 2: Install (Choose One Method)

#### Method A: Quick Install (Recommended)

**Windows:**
1. Open Command Prompt in the transcribe_ro folder
2. Run: `setup_portable.bat`
3. Wait for installation to complete

**Mac/Linux:**
1. Open Terminal in the transcribe_ro folder
2. Run: `chmod +x setup_portable.sh && ./setup_portable.sh`
3. Wait for installation to complete

#### Method B: Manual Install

```bash
# Create virtual environment
python -m venv venv

# Activate it
# Windows: venv\Scripts\activate
# Mac/Linux: source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Transcribe Your First Audio File

**Easy Way (Using Helper Scripts):**

**Windows:**
```cmd
run_transcribe.bat your_audio.mp3
```

**Mac/Linux:**
```bash
./run_transcribe.sh your_audio.mp3
```

**Manual Way:**
```bash
# Activate virtual environment first
# Windows: venv\Scripts\activate
# Mac/Linux: source venv/bin/activate

python transcribe_ro.py your_audio.mp3
```

### Step 4: Find Your Transcription

Look for a file named `your_audio_transcription.txt` in the same folder as your audio file!

## Common Use Cases

### 1. Quick Transcription (Fastest)
```bash
python transcribe_ro.py audio.mp3 --model tiny
```

### 2. High Quality Transcription
```bash
python transcribe_ro.py audio.mp3 --model medium
```

### 3. Transcribe Only (No Translation)
```bash
python transcribe_ro.py audio.mp3 --no-translate
```

### 4. Create Subtitles for Video
```bash
python transcribe_ro.py audio.mp3 --format srt
```

### 5. Export as JSON (For Developers)
```bash
python transcribe_ro.py audio.mp3 --format json
```

## Troubleshooting

### "FFmpeg not found"
**Solution:** Install FFmpeg
- **Windows:** Download from [ffmpeg.org](https://ffmpeg.org/download.html)
- **Mac:** Run `brew install ffmpeg`
- **Linux:** Run `sudo apt install ffmpeg`

### "Module not found" or Import Errors
**Solution:** Make sure you activated the virtual environment:
- **Windows:** `venv\Scripts\activate`
- **Mac/Linux:** `source venv/bin/activate`

### Slow Processing
**Solution:** Use a smaller model:
```bash
python transcribe_ro.py audio.mp3 --model tiny
```

### Out of Memory
**Solution:** 
1. Use smaller model: `--model tiny`
2. Close other programs
3. Split long audio into shorter segments

## Tips for Best Results

✅ **Use good quality audio** - Clear audio = better transcription
✅ **Start with 'base' model** - Good balance of speed and accuracy
✅ **Use 'medium' for important work** - Better accuracy for professional use
✅ **Check your output file** - Always review the transcription
✅ **Keep files under 1 hour** - Faster processing, easier to manage

## What Happens on First Run?

On your first transcription:
1. ⏬ Whisper model will be downloaded (300MB-3GB depending on model)
2. 🔄 This only happens once - models are cached
3. ⏱️ First run may take 2-10 minutes depending on your internet speed
4. ⚡ Subsequent runs will be much faster!

## Getting Help

If you need help:
1. Read the full [README.md](README.md)
2. Check error messages carefully
3. Try with a different audio file
4. Make sure FFmpeg is installed
5. Open an issue on GitHub with:
   - Your operating system
   - The error message
   - The command you ran

## Next Steps

Once you're comfortable with the basics:
- 📚 Read the full [README.md](README.md) for advanced features
- 🎯 Experiment with different models and output formats
- 💾 Set up portable installation on a USB drive
- 🔧 Customize the output format for your needs

---

**Happy Transcribing! 🎉**
