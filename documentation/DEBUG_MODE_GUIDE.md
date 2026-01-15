# Debug Mode Guide

## Overview

The `--debug` flag enables detailed diagnostic output to help troubleshoot issues with transcription and translation. This is especially useful when translation to Romanian is not working as expected.

## Usage

```bash
python transcribe_ro.py <audio_file> --debug
```

## What Debug Mode Shows

### 1. **Initialization Details**
- Python version
- Working directory
- Model name and device
- Translator availability
- Command line arguments

### 2. **Model Loading**
- Start time
- Loading duration
- Model type
- Success/failure status

### 3. **Audio Transcription**
- Audio file path
- File size in MB
- Task mode (transcribe/translate)
- Transcription start time
- Transcription duration
- Number of segments detected
- Text length

### 4. **Language Detection**
- Detected language code (e.g., 'en', 'ro', 'es')
- Language name (e.g., 'English', 'Romanian')
- Language confidence score (if available)
- Number of segments
- Sample of transcribed text (first 200 characters)

### 5. **Translation Decision**
- Whether translation will be attempted
- Reason for translation or skipping:
  - "Translation will be attempted" (different language detected)
  - "Audio is already in Romanian" (detected language is 'ro')
  - "--no-translate flag was set" (user disabled translation)

### 6. **Translation Process**
- Text length before translation
- Source language
- Translator instance creation
- Translation attempts with retry numbers (1/3, 2/3, 3/3)
- Duration of each attempt
- Result type and length
- Whether result is different from original
- Sample of translated text (first 200 characters)
- Wait times between retries

### 7. **Multi-Chunk Translation** (for long texts)
- Number of chunks
- Size of each chunk
- Progress through chunks
- Individual chunk translation status

### 8. **File Writing**
- Output path (relative and absolute)
- Output format
- Output directory status
- Metadata details
- Write duration
- File size in KB
- File existence confirmation

### 9. **Error Handling**
- Full exception type
- Exception details
- Complete stack trace
- Context where error occurred

### 10. **Summary**
- Total processing time
- Detected language
- Output file path
- Transcription length
- Translation length
- Whether translation changed the text

## Example Debug Output

```
2026-01-12 14:04:00.530 [DEBUG] ================================================================================
2026-01-12 14:04:00.530 [DEBUG] DEBUG MODE ENABLED - Detailed output will be shown
2026-01-12 14:04:00.530 [DEBUG] ================================================================================
2026-01-12 14:04:00.530 [DEBUG] Model name: tiny
2026-01-12 14:04:00.530 [DEBUG] Device: cpu
2026-01-12 14:04:00.530 [DEBUG] Translator available: True
2026-01-12 14:04:00.530 [DEBUG] Python version: 3.11.6 (main, Dec  9 2025, 11:42:39) [GCC 12.2.0]

2026-01-12 14:04:02.024 [DEBUG] Model loaded in 1.49 seconds

2026-01-12 14:04:02.025 [DEBUG] ================================================================================
2026-01-12 14:04:02.025 [DEBUG] STEP: LANGUAGE DETECTION RESULTS
2026-01-12 14:04:02.025 [DEBUG] ================================================================================
2026-01-12 14:04:02.025 [DEBUG] Detected language code: en
2026-01-12 14:04:02.025 [DEBUG] Language name: English
2026-01-12 14:04:02.025 [DEBUG] Transcription sample (first 200 chars): 'Hello, this is a test...'

2026-01-12 14:04:02.025 [DEBUG] ================================================================================
2026-01-12 14:04:02.025 [DEBUG] STEP: TRANSLATION DECISION
2026-01-12 14:04:02.025 [DEBUG] ================================================================================
2026-01-12 14:04:02.025 [DEBUG] Translate flag: True
2026-01-12 14:04:02.025 [DEBUG] Detected language: en
2026-01-12 14:04:02.025 [DEBUG] Is Romanian: False
2026-01-12 14:04:02.025 [DEBUG] DECISION: Translation will be attempted
2026-01-12 14:04:02.025 [DEBUG] REASON: translate=True and detected_language='en' != 'ro'

2026-01-12 14:04:03.125 [DEBUG] Translation attempt 1/3 started
2026-01-12 14:04:03.125 [DEBUG] Creating GoogleTranslator(source='auto', target='ro')
2026-01-12 14:04:04.532 [DEBUG] Translation call completed in 1.41 seconds
2026-01-12 14:04:04.532 [DEBUG] Translation sample (first 200 chars): 'Bună, acesta este un test...'
```

## Troubleshooting with Debug Mode

### Problem: Translation Not Working

**Check these debug outputs:**

1. **Translator availability**
   ```
   [DEBUG] Translator available: True
   ```
   If `False`, install deep-translator: `pip install deep-translator`

2. **Translation decision**
   ```
   [DEBUG] DECISION: Translation will be attempted
   ```
   If it says "skipped", check the reason

3. **Translation attempts**
   ```
   [DEBUG] Translation attempt 1/3 started
   [DEBUG] Translation call completed in 1.41 seconds
   ```
   Check if attempts are failing with errors

4. **Translation result**
   ```
   [DEBUG] Original != Translated: True
   [DEBUG] Translation sample (first 200 chars): ...
   ```
   Check if the translation is actually different

### Problem: Transcription Failing

**Check these debug outputs:**

1. **Model loading**
   ```
   [DEBUG] Model loaded in 1.49 seconds
   [DEBUG] Model type: <class 'whisper.model.Whisper'>
   ```

2. **Audio file**
   ```
   [DEBUG] Audio file: test.mp3
   [DEBUG] File size: 2.45 MB
   ```

3. **Error details**
   ```
   [DEBUG] FULL EXCEPTION DETAILS
   [DEBUG] Traceback (most recent call last):
   ...
   ```

### Problem: Wrong Language Detected

**Check these debug outputs:**

1. **Language detection**
   ```
   [DEBUG] Detected language code: en
   [DEBUG] Language name: English
   [DEBUG] Language confidence: 0.9823
   ```

2. **Transcription sample**
   ```
   [DEBUG] Transcription sample (first 200 chars): ...
   ```
   Verify the transcription looks correct

## Performance Monitoring

Debug mode shows timing for each step:

- **Model loading**: How long it takes to load the Whisper model
- **Transcription**: How long it takes to transcribe the audio
- **Translation**: How long each translation attempt takes
- **File writing**: How long it takes to write the output file
- **Total time**: Overall processing time

## Tips

1. **Always use `--debug` when troubleshooting** - It provides crucial information
2. **Save debug output** - Redirect to a file: `python transcribe_ro.py audio.mp3 --debug > debug.log 2>&1`
3. **Check timing** - Helps identify slow steps
4. **Look for "REASON"** - Shows why decisions were made
5. **Check samples** - Text samples help verify correct operation

## When to Use Debug Mode

- ✅ Translation is not working
- ✅ Wrong language is detected
- ✅ Process is taking too long
- ✅ Getting errors or exceptions
- ✅ Want to understand what's happening
- ✅ Reporting bugs or issues
- ❌ Normal production use (creates verbose output)

## Disabling Debug Mode

Simply remove the `--debug` flag for normal operation:

```bash
python transcribe_ro.py audio.mp3
```

## Debug Log Format

Debug messages include:
- **Timestamp**: `YYYY-MM-DD HH:MM:SS.mmm` (with milliseconds)
- **Level**: `[DEBUG]`
- **Message**: Descriptive information
- **Separators**: `====` for major steps, `----` for subsections

## Getting Help

If you're still having issues after reviewing debug output:

1. Save the debug log
2. Check the troubleshooting section in README.md
3. Review TRANSLATION_FIX_SUMMARY.md
4. Open an issue with the debug log attached
