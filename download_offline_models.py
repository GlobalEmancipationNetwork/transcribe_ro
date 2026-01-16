#!/usr/bin/env python3
"""
Download Offline Translation Models
Downloads MarianMT models for offline translation to Romanian.
Run this script with internet connection to cache models for offline use.

Usage:
    python download_offline_models.py [language_codes...]
    
Examples:
    python download_offline_models.py                  # Download all common models
    python download_offline_models.py en es fr         # Download specific languages
    python download_offline_models.py --list          # List available languages
"""

import argparse
import os
import sys
from pathlib import Path

try:
    from transformers import MarianMTModel, MarianTokenizer
    import sentencepiece
except ImportError:
    print("ERROR: Required dependencies not installed!")
    print("Please install with: pip install transformers sentencepiece")
    sys.exit(1)


# Language to model mapping
LANGUAGE_MODELS = {
    'en': ('opus-mt-en-roa', 'English'),
    'es': ('opus-mt-es-ro', 'Spanish'),
    'fr': ('opus-mt-fr-ro', 'French'),
    'de': ('opus-mt-de-ro', 'German'),
    'it': ('opus-mt-it-ro', 'Italian'),
    'pt': ('opus-mt-itc-itc', 'Portuguese'),
    'ru': ('opus-mt-ru-ro', 'Russian'),
    'zh': ('opus-mt-zh-ro', 'Chinese'),
    'ja': ('opus-mt-jap-ro', 'Japanese'),
    'ar': ('opus-mt-ar-ro', 'Arabic'),
    'hi': ('opus-mt-hi-ro', 'Hindi'),
    'nl': ('opus-mt-nl-ro', 'Dutch'),
    'pl': ('opus-mt-pl-ro', 'Polish'),
    'tr': ('opus-mt-tr-ro', 'Turkish'),
}

# Most common languages to download by default
DEFAULT_LANGUAGES = ['en', 'es', 'fr', 'de', 'it']


def download_model(lang_code, model_name, cache_dir=None):
    """
    Download a MarianMT model for a specific language.
    
    Args:
        lang_code: Language code (e.g., 'en', 'es')
        model_name: Model name (e.g., 'opus-mt-en-roa')
        cache_dir: Optional cache directory
    
    Returns:
        bool: True if successful, False otherwise
    """
    full_model_name = f"Helsinki-NLP/{model_name}"
    
    print(f"\n{'='*80}")
    print(f"Downloading {LANGUAGE_MODELS[lang_code][1]} -> Romanian model")
    print(f"Model: {model_name}")
    print(f"{'='*80}")
    
    try:
        print(f"[1/2] Downloading tokenizer...")
        tokenizer = MarianTokenizer.from_pretrained(
            full_model_name,
            cache_dir=cache_dir
        )
        print(f"✓ Tokenizer downloaded successfully")
        
        print(f"[2/2] Downloading model (this may take a while)...")
        model = MarianMTModel.from_pretrained(
            full_model_name,
            cache_dir=cache_dir
        )
        print(f"✓ Model downloaded successfully")
        
        # Test the model with a simple translation
        print(f"[3/3] Testing model...")
        test_input = tokenizer("Hello, world!", return_tensors="pt", padding=True)
        test_output = model.generate(**test_input)
        test_translation = tokenizer.decode(test_output[0], skip_special_tokens=True)
        print(f"✓ Model test successful: 'Hello, world!' -> '{test_translation}'")
        
        return True
        
    except Exception as e:
        print(f"✗ Failed to download model: {e}")
        return False


def list_available_languages():
    """List all available language models."""
    print("\n" + "="*80)
    print("AVAILABLE OFFLINE TRANSLATION MODELS")
    print("="*80)
    print(f"\n{'Code':<6} {'Language':<20} {'Model Name'}")
    print("-" * 80)
    
    for code, (model, lang_name) in sorted(LANGUAGE_MODELS.items()):
        print(f"{code:<6} {lang_name:<20} Helsinki-NLP/{model}")
    
    print("\n" + "="*80)
    print(f"Total: {len(LANGUAGE_MODELS)} language pairs available")
    print("="*80)
    print("\nDefault languages (downloaded if no specific languages specified):")
    print(", ".join([f"{code} ({LANGUAGE_MODELS[code][1]})" for code in DEFAULT_LANGUAGES]))
    print()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Download offline translation models for Romanian",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download all common models (en, es, fr, de, it)
  python download_offline_models.py
  
  # Download specific languages
  python download_offline_models.py en es fr
  
  # List available languages
  python download_offline_models.py --list
  
  # Download all available models
  python download_offline_models.py --all
  
  # Specify custom cache directory
  python download_offline_models.py --cache-dir /path/to/cache en es
        """
    )
    
    parser.add_argument(
        'languages',
        nargs='*',
        help='Language codes to download (e.g., en es fr). If not specified, downloads common languages.'
    )
    
    parser.add_argument(
        '--list',
        action='store_true',
        help='List all available languages and exit'
    )
    
    parser.add_argument(
        '--all',
        action='store_true',
        help='Download all available language models'
    )
    
    parser.add_argument(
        '--cache-dir',
        type=str,
        default=None,
        help='Custom cache directory for models (default: ~/.cache/huggingface/hub)'
    )
    
    args = parser.parse_args()
    
    # List languages if requested
    if args.list:
        list_available_languages()
        return
    
    # Determine which languages to download
    if args.all:
        languages_to_download = list(LANGUAGE_MODELS.keys())
    elif args.languages:
        languages_to_download = args.languages
        # Validate language codes
        invalid = [lang for lang in languages_to_download if lang not in LANGUAGE_MODELS]
        if invalid:
            print(f"ERROR: Invalid language codes: {', '.join(invalid)}")
            print(f"Use --list to see available languages")
            sys.exit(1)
    else:
        # Default to common languages
        languages_to_download = DEFAULT_LANGUAGES
    
    # Setup cache directory
    if args.cache_dir:
        cache_dir = Path(args.cache_dir).expanduser().absolute()
        cache_dir.mkdir(parents=True, exist_ok=True)
        print(f"Using custom cache directory: {cache_dir}")
    else:
        cache_dir = None
        print(f"Using default cache directory: ~/.cache/huggingface/hub")
    
    # Print banner
    print("\n" + "="*80)
    print("OFFLINE TRANSLATION MODEL DOWNLOADER")
    print("="*80)
    print(f"\nLanguages to download: {len(languages_to_download)}")
    for lang_code in languages_to_download:
        lang_name = LANGUAGE_MODELS[lang_code][1]
        print(f"  - {lang_code}: {lang_name}")
    print()
    
    # Download models
    success_count = 0
    failed = []
    
    for i, lang_code in enumerate(languages_to_download, 1):
        model_name = LANGUAGE_MODELS[lang_code][0]
        
        print(f"\nProgress: {i}/{len(languages_to_download)}")
        
        if download_model(lang_code, model_name, cache_dir):
            success_count += 1
        else:
            failed.append(lang_code)
    
    # Print summary
    print("\n" + "="*80)
    print("DOWNLOAD SUMMARY")
    print("="*80)
    print(f"Total attempted: {len(languages_to_download)}")
    print(f"Successful: {success_count}")
    print(f"Failed: {len(failed)}")
    
    if failed:
        print(f"\nFailed languages: {', '.join(failed)}")
        print("Please check your internet connection and try again.")
    else:
        print("\n✓ All models downloaded successfully!")
        print("\nYou can now use offline translation with:")
        print("  python transcribe_ro.py audio.mp3 --translation-mode offline")
        print("  python transcribe_ro.py audio.mp3 --translation-mode auto  # (default, auto fallback)")
    
    print("="*80)
    
    # Exit with appropriate code
    sys.exit(0 if len(failed) == 0 else 1)


if __name__ == '__main__':
    main()
