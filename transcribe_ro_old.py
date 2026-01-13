#!/usr/bin/env python3
"""
Transcribe RO - Audio Transcription and Translation Tool for Romanian

A portable CLI tool that transcribes audio files in any language and translates them to Romanian.
Uses OpenAI Whisper for automatic language detection and transcription.

Author: transcribe_ro
License: MIT
"""

import argparse
import os
import sys
import json
from datetime import datetime
from pathlib import Path
import warnings

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

try:
    import whisper
    from whisper.utils import get_writer
except ImportError:
    print("Error: OpenAI Whisper not installed. Please run: pip install -r requirements.txt")
    sys.exit(1)

try:
    from googletrans import Translator
except ImportError:
    print("Warning: googletrans not installed. Translation features will be limited.")
    print("Install with: pip install googletrans==4.0.0rc1")
    Translator = None


class AudioTranscriber:
    """Main class for audio transcription and translation."""
    
    def __init__(self, model_name="base", device="cpu"):
        """
        Initialize the transcriber.
        
        Args:
            model_name: Whisper model to use (tiny, base, small, medium, large)
            device: Device to run on (cpu or cuda)
        """
        self.model_name = model_name
        self.device = device
        self.model = None
        self.translator = Translator() if Translator else None
        
        print(f"Loading Whisper model '{model_name}' on {device}...")
        try:
            self.model = whisper.load_model(model_name, device=device)
            print("Model loaded successfully!\n")
        except Exception as e:
            print(f"Error loading model: {e}")
            sys.exit(1)
    
    def transcribe_audio(self, audio_path, task="transcribe"):
        """
        Transcribe audio file using Whisper.
        
        Args:
            audio_path: Path to audio file
            task: 'transcribe' or 'translate' (translate translates to English in Whisper)
        
        Returns:
            Dictionary containing transcription results
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        print(f"Transcribing: {audio_path}")
        print("This may take a few minutes depending on the file size...\n")
        
        try:
            result = self.model.transcribe(
                audio_path,
                task=task,
                verbose=False
            )
            return result
        except Exception as e:
            raise Exception(f"Error during transcription: {e}")
    
    def translate_to_romanian(self, text, source_lang="auto"):
        """
        Translate text to Romanian using Google Translate.
        
        Args:
            text: Text to translate
            source_lang: Source language code (default: auto-detect)
        
        Returns:
            Translated text
        """
        if not self.translator:
            print("Warning: Translation service not available. Returning original text.")
            return text
        
        try:
            # Split text into chunks if it's too long (Google Translate has limits)
            max_length = 5000
            if len(text) <= max_length:
                translation = self.translator.translate(text, src=source_lang, dest='ro')
                return translation.text
            else:
                # Split by sentences and translate in chunks
                sentences = text.split('. ')
                translated_chunks = []
                current_chunk = ""
                
                for sentence in sentences:
                    if len(current_chunk) + len(sentence) < max_length:
                        current_chunk += sentence + ". "
                    else:
                        if current_chunk:
                            translation = self.translator.translate(current_chunk, src=source_lang, dest='ro')
                            translated_chunks.append(translation.text)
                        current_chunk = sentence + ". "
                
                if current_chunk:
                    translation = self.translator.translate(current_chunk, src=source_lang, dest='ro')
                    translated_chunks.append(translation.text)
                
                return " ".join(translated_chunks)
        except Exception as e:
            print(f"Warning: Translation failed: {e}")
            return text
    
    def process_audio(
        self,
        audio_path,
        output_path=None,
        translate=True,
        include_timestamps=True,
        output_format="txt"
    ):
        """
        Process audio file: transcribe and optionally translate to Romanian.
        
        Args:
            audio_path: Path to audio file
            output_path: Path for output file (default: same as input with .txt extension)
            translate: Whether to translate to Romanian
            include_timestamps: Whether to include timestamps in output
            output_format: Output format (txt, json, srt, vtt)
        
        Returns:
            Dictionary with processing results
        """
        # Transcribe audio
        result = self.transcribe_audio(audio_path)
        
        # Extract information
        detected_language = result.get('language', 'unknown')
        transcribed_text = result.get('text', '').strip()
        segments = result.get('segments', [])
        
        print(f"Detected language: {detected_language}")
        print(f"Transcription length: {len(transcribed_text)} characters\n")
        
        # Translate to Romanian if needed and requested
        translated_text = None
        if translate and detected_language != 'ro':
            print("Translating to Romanian...")
            translated_text = self.translate_to_romanian(transcribed_text, source_lang=detected_language)
            print("Translation completed!\n")
        elif detected_language == 'ro':
            print("Audio is already in Romanian. No translation needed.\n")
            translated_text = transcribed_text
        
        # Prepare output
        if output_path is None:
            audio_name = Path(audio_path).stem
            output_path = Path(audio_path).parent / f"{audio_name}_transcription.{output_format}"
        else:
            output_path = Path(output_path)
        
        # Generate metadata
        metadata = {
            'source_file': str(audio_path),
            'detected_language': detected_language,
            'transcription_date': datetime.now().isoformat(),
            'model_used': self.model_name,
            'translation_applied': translate and detected_language != 'ro'
        }
        
        # Write output based on format
        if output_format == 'json':
            self._write_json_output(output_path, transcribed_text, translated_text, segments, metadata)
        elif output_format in ['srt', 'vtt']:
            self._write_subtitle_output(output_path, segments, translate, output_format)
        else:  # txt format
            self._write_text_output(
                output_path,
                transcribed_text,
                translated_text,
                segments if include_timestamps else None,
                metadata
            )
        
        print(f"Output saved to: {output_path}")
        
        return {
            'output_file': str(output_path),
            'detected_language': detected_language,
            'transcribed_text': transcribed_text,
            'translated_text': translated_text,
            'metadata': metadata
        }
    
    def _write_text_output(self, output_path, transcription, translation, segments, metadata):
        """Write transcription to text file."""
        with open(output_path, 'w', encoding='utf-8') as f:
            # Write header
            f.write("="*80 + "\n")
            f.write("TRANSCRIPTION RESULTS\n")
            f.write("="*80 + "\n\n")
            
            # Write metadata
            f.write("METADATA:\n")
            f.write("-" * 40 + "\n")
            for key, value in metadata.items():
                f.write(f"{key.replace('_', ' ').title()}: {value}\n")
            f.write("\n")
            
            # Write original transcription
            f.write("ORIGINAL TRANSCRIPTION:\n")
            f.write("-" * 40 + "\n")
            f.write(transcription + "\n\n")
            
            # Write translation if available
            if translation and translation != transcription:
                f.write("ROMANIAN TRANSLATION:\n")
                f.write("-" * 40 + "\n")
                f.write(translation + "\n\n")
            
            # Write timestamps if available
            if segments:
                f.write("TIMESTAMPS:\n")
                f.write("-" * 40 + "\n")
                for segment in segments:
                    start_time = self._format_timestamp(segment['start'])
                    end_time = self._format_timestamp(segment['end'])
                    text = segment['text'].strip()
                    f.write(f"[{start_time} -> {end_time}] {text}\n")
                f.write("\n")
            
            f.write("="*80 + "\n")
            f.write("End of transcription\n")
            f.write("="*80 + "\n")
    
    def _write_json_output(self, output_path, transcription, translation, segments, metadata):
        """Write transcription to JSON file."""
        data = {
            'metadata': metadata,
            'transcription': transcription,
            'translation': translation,
            'segments': segments
        }
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _write_subtitle_output(self, output_path, segments, translate, format_type):
        """Write transcription to subtitle file (SRT or VTT)."""
        with open(output_path, 'w', encoding='utf-8') as f:
            if format_type == 'vtt':
                f.write("WEBVTT\n\n")
            
            for i, segment in enumerate(segments, 1):
                start_time = self._format_timestamp(segment['start'], format_type)
                end_time = self._format_timestamp(segment['end'], format_type)
                text = segment['text'].strip()
                
                # Translate segment if requested
                if translate and self.translator:
                    try:
                        text = self.translate_to_romanian(text)
                    except:
                        pass  # Keep original if translation fails
                
                if format_type == 'srt':
                    f.write(f"{i}\n")
                    f.write(f"{start_time} --> {end_time}\n")
                    f.write(f"{text}\n\n")
                else:  # vtt
                    f.write(f"{start_time} --> {end_time}\n")
                    f.write(f"{text}\n\n")
    
    @staticmethod
    def _format_timestamp(seconds, format_type='txt'):
        """Format timestamp in seconds to readable format."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        
        if format_type == 'srt':
            return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
        elif format_type == 'vtt':
            return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"
        else:  # txt
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Transcribe RO - Audio Transcription and Translation Tool for Romanian",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic transcription
  python transcribe_ro.py audio.mp3
  
  # Transcribe without translation
  python transcribe_ro.py audio.mp3 --no-translate
  
  # Use a larger model for better accuracy
  python transcribe_ro.py audio.mp3 --model medium
  
  # Output as JSON
  python transcribe_ro.py audio.mp3 --format json
  
  # Generate subtitle file
  python transcribe_ro.py audio.mp3 --format srt
  
  # Specify output file
  python transcribe_ro.py audio.mp3 --output result.txt
        """
    )
    
    # Required arguments
    parser.add_argument(
        'audio_file',
        type=str,
        help='Path to audio file (MP3, WAV, M4A, FLAC, etc.)'
    )
    
    # Optional arguments
    parser.add_argument(
        '-o', '--output',
        type=str,
        default=None,
        help='Output file path (default: <audio_file>_transcription.txt)'
    )
    
    parser.add_argument(
        '-m', '--model',
        type=str,
        choices=['tiny', 'base', 'small', 'medium', 'large'],
        default='base',
        help='Whisper model size (default: base). Larger models are more accurate but slower.'
    )
    
    parser.add_argument(
        '-f', '--format',
        type=str,
        choices=['txt', 'json', 'srt', 'vtt'],
        default='txt',
        help='Output format (default: txt)'
    )
    
    parser.add_argument(
        '--no-translate',
        action='store_true',
        help='Skip translation to Romanian (only transcribe)'
    )
    
    parser.add_argument(
        '--no-timestamps',
        action='store_true',
        help='Exclude timestamps from output (txt format only)'
    )
    
    parser.add_argument(
        '--device',
        type=str,
        choices=['cpu', 'cuda'],
        default='cpu',
        help='Device to run on (default: cpu). Use cuda if GPU is available.'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='Transcribe RO v1.0.0'
    )
    
    args = parser.parse_args()
    
    # Validate audio file
    if not os.path.exists(args.audio_file):
        print(f"Error: Audio file not found: {args.audio_file}")
        sys.exit(1)
    
    # Check file extension
    supported_formats = ['.mp3', '.wav', '.m4a', '.flac', '.ogg', '.wma', '.aac', '.opus']
    file_ext = Path(args.audio_file).suffix.lower()
    if file_ext not in supported_formats:
        print(f"Warning: File format '{file_ext}' may not be supported.")
        print(f"Supported formats: {', '.join(supported_formats)}")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            sys.exit(0)
    
    # Print banner
    print("\n" + "="*80)
    print("TRANSCRIBE RO - Audio Transcription & Translation Tool")
    print("="*80 + "\n")
    
    try:
        # Initialize transcriber
        transcriber = AudioTranscriber(model_name=args.model, device=args.device)
        
        # Process audio
        result = transcriber.process_audio(
            audio_path=args.audio_file,
            output_path=args.output,
            translate=not args.no_translate,
            include_timestamps=not args.no_timestamps,
            output_format=args.format
        )
        
        print("\n" + "="*80)
        print("PROCESSING COMPLETED SUCCESSFULLY!")
        print("="*80)
        print(f"\nDetected language: {result['detected_language']}")
        print(f"Output file: {result['output_file']}")
        
    except KeyboardInterrupt:
        print("\n\nProcess interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
