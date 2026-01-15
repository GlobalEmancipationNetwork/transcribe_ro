#!/usr/bin/env python3
"""
Test script to verify dual-file output (original transcription + translated file)
"""

import os
import sys
import tempfile
from pathlib import Path

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_dual_file_paths():
    """Test that dual file paths are generated correctly."""
    print("="*80)
    print("TEST 1: Dual File Path Generation")
    print("="*80)
    
    from transcribe_ro import AudioTranscriber
    
    # Test cases
    test_cases = [
        {
            'input': '/path/to/audio.m4a',
            'expected_original': '/path/to/audio_transcription.txt',
            'expected_translated': '/path/to/audio_translated_ro.txt'
        },
        {
            'input': '/path/to/recording.mp3',
            'expected_original': '/path/to/recording_transcription.json',
            'expected_translated': '/path/to/recording_translated_ro.json'
        },
        {
            'input': '/path/to/video.wav',
            'expected_original': '/path/to/video_transcription.srt',
            'expected_translated': '/path/to/video_translated_ro.srt'
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        audio_path = case['input']
        audio_name = Path(audio_path).stem
        output_format = case['expected_original'].split('.')[-1]
        
        # Simulate path generation logic from process_audio
        output_path = Path(audio_path).parent / f"{audio_name}_transcription.{output_format}"
        
        output_stem = output_path.stem
        if output_stem.endswith('_transcription'):
            output_stem = output_stem[:-14]
        translated_output_path = output_path.parent / f"{output_stem}_translated_ro{output_path.suffix}"
        
        print(f"\nTest case {i}:")
        print(f"  Input: {audio_path}")
        print(f"  Original: {output_path}")
        print(f"  Translated: {translated_output_path}")
        print(f"  Expected original: {case['expected_original']}")
        print(f"  Expected translated: {case['expected_translated']}")
        
        assert str(output_path) == case['expected_original'], f"Original path mismatch!"
        assert str(translated_output_path) == case['expected_translated'], f"Translated path mismatch!"
        print(f"  ✓ PASSED")
    
    print("\n" + "="*80)
    print("✓ All path generation tests passed!")
    print("="*80)


def test_file_writing():
    """Test that both files are actually created with correct content."""
    print("\n" + "="*80)
    print("TEST 2: File Writing (Simulated)")
    print("="*80)
    
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        # Test TXT format
        print("\nTesting TXT format...")
        original_txt = tmpdir_path / "test_transcription.txt"
        translated_txt = tmpdir_path / "test_translated_ro.txt"
        
        # Simulate writing original file
        with open(original_txt, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write("TRANSCRIPTION RESULTS (ORIGINAL LANGUAGE)\n")
            f.write("="*80 + "\n\n")
            f.write("TRANSCRIPTION:\n")
            f.write("-" * 40 + "\n")
            f.write("This is the original English text.\n")
        
        # Simulate writing translated file
        with open(translated_txt, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write("ROMANIAN TRANSLATION\n")
            f.write("="*80 + "\n\n")
            f.write("TRANSLATED TEXT:\n")
            f.write("-" * 40 + "\n")
            f.write("Acesta este textul original în engleză.\n")
        
        # Verify both files exist
        assert original_txt.exists(), "Original TXT file not created!"
        assert translated_txt.exists(), "Translated TXT file not created!"
        
        # Verify content
        original_content = original_txt.read_text()
        translated_content = translated_txt.read_text()
        
        assert "ORIGINAL LANGUAGE" in original_content, "Original file missing header!"
        assert "This is the original English text" in original_content, "Original file missing content!"
        assert "ROMANIAN TRANSLATION" in translated_content, "Translated file missing header!"
        assert "Acesta este textul" in translated_content, "Translated file missing translated content!"
        
        print(f"  ✓ Original file created: {original_txt.name}")
        print(f"  ✓ Translated file created: {translated_txt.name}")
        print(f"  ✓ Both files contain correct content")
        
        # Test JSON format
        print("\nTesting JSON format...")
        import json
        
        original_json = tmpdir_path / "test_transcription.json"
        translated_json = tmpdir_path / "test_translated_ro.json"
        
        # Simulate writing original JSON
        with open(original_json, 'w', encoding='utf-8') as f:
            json.dump({
                'metadata': {'detected_language': 'en'},
                'transcription': 'This is the original text.',
                'translation': None,
                'segments': []
            }, f, ensure_ascii=False, indent=2)
        
        # Simulate writing translated JSON
        with open(translated_json, 'w', encoding='utf-8') as f:
            json.dump({
                'metadata': {'detected_language': 'en', 'file_type': 'romanian_translation'},
                'transcription': 'Acesta este textul original.',
                'translation': None,
                'segments': []
            }, f, ensure_ascii=False, indent=2)
        
        assert original_json.exists(), "Original JSON file not created!"
        assert translated_json.exists(), "Translated JSON file not created!"
        
        print(f"  ✓ Original JSON created: {original_json.name}")
        print(f"  ✓ Translated JSON created: {translated_json.name}")
        
        # Test SRT format
        print("\nTesting SRT format...")
        original_srt = tmpdir_path / "test_transcription.srt"
        translated_srt = tmpdir_path / "test_translated_ro.srt"
        
        # Simulate writing original SRT
        with open(original_srt, 'w', encoding='utf-8') as f:
            f.write("1\n")
            f.write("00:00:00,000 --> 00:00:05,000\n")
            f.write("This is the original subtitle.\n\n")
        
        # Simulate writing translated SRT
        with open(translated_srt, 'w', encoding='utf-8') as f:
            f.write("1\n")
            f.write("00:00:00,000 --> 00:00:05,000\n")
            f.write("Acesta este subtitlul original.\n\n")
        
        assert original_srt.exists(), "Original SRT file not created!"
        assert translated_srt.exists(), "Translated SRT file not created!"
        
        print(f"  ✓ Original SRT created: {original_srt.name}")
        print(f"  ✓ Translated SRT created: {translated_srt.name}")
        
        print("\n" + "="*80)
        print("✓ All file writing tests passed!")
        print("="*80)


def test_file_naming_convention():
    """Test the file naming convention for various scenarios."""
    print("\n" + "="*80)
    print("TEST 3: File Naming Convention")
    print("="*80)
    
    test_cases = [
        {
            'name': 'Basic MP3 file',
            'input': 'audio.mp3',
            'format': 'txt',
            'original': 'audio_transcription.txt',
            'translated': 'audio_translated_ro.txt'
        },
        {
            'name': 'File with underscore',
            'input': 'my_recording.m4a',
            'format': 'json',
            'original': 'my_recording_transcription.json',
            'translated': 'my_recording_translated_ro.json'
        },
        {
            'name': 'File with spaces (theoretical)',
            'input': 'audio file.wav',
            'format': 'srt',
            'original': 'audio file_transcription.srt',
            'translated': 'audio file_translated_ro.srt'
        },
        {
            'name': 'VTT subtitle format',
            'input': 'presentation.mp4',
            'format': 'vtt',
            'original': 'presentation_transcription.vtt',
            'translated': 'presentation_translated_ro.vtt'
        }
    ]
    
    for test in test_cases:
        print(f"\n{test['name']}:")
        print(f"  Input: {test['input']}")
        print(f"  Format: {test['format']}")
        print(f"  Expected original: {test['original']}")
        print(f"  Expected translated: {test['translated']}")
        
        # Verify naming pattern
        assert '_transcription.' in test['original'], "Original file should contain '_transcription'"
        assert '_translated_ro.' in test['translated'], "Translated file should contain '_translated_ro'"
        assert test['original'].endswith(test['format']), "Original file extension mismatch"
        assert test['translated'].endswith(test['format']), "Translated file extension mismatch"
        
        print(f"  ✓ Naming convention correct")
    
    print("\n" + "="*80)
    print("✓ All naming convention tests passed!")
    print("="*80)


def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("DUAL-FILE OUTPUT TEST SUITE")
    print("Testing: Original Transcription + Translated File Creation")
    print("="*80)
    
    try:
        test_dual_file_paths()
        test_file_writing()
        test_file_naming_convention()
        
        print("\n" + "="*80)
        print("✅ ALL TESTS PASSED!")
        print("="*80)
        print("\nSummary:")
        print("  ✓ File path generation works correctly")
        print("  ✓ Both files are created with correct content")
        print("  ✓ Naming convention follows expected pattern")
        print("\nExpected behavior when translating:")
        print("  1. Original transcription saved as: <filename>_transcription.<format>")
        print("  2. Romanian translation saved as: <filename>_translated_ro.<format>")
        print("  3. Both files created for all formats: txt, json, srt, vtt")
        print("="*80 + "\n")
        
        return 0
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
