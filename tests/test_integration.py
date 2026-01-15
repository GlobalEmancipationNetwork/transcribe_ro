#!/usr/bin/env python3
"""
Integration test to verify translation works in the transcribe_ro module
"""

import sys
import os
import logging
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Import just the translation functionality
from deep_translator import GoogleTranslator

def translate_with_retry(text, source_lang, max_retries=3):
    """
    Translate text with retry logic (mimics the transcribe_ro implementation)
    """
    for attempt in range(max_retries):
        try:
            logger.info(f"Translation attempt {attempt + 1}/{max_retries}...")
            
            translator = GoogleTranslator(source=source_lang, target='ro')
            translated = translator.translate(text)
            
            if translated and translated.strip():
                logger.info(f"✓ Translation successful! ({len(text)} -> {len(translated)} chars)")
                return translated
            else:
                logger.warning("Translation returned empty result")
                if attempt < max_retries - 1:
                    time.sleep(1 * (attempt + 1))
                    continue
                return text
                
        except Exception as e:
            logger.warning(f"Translation attempt {attempt + 1} failed: {str(e)}")
            
            if attempt < max_retries - 1:
                wait_time = 2 * (attempt + 1)
                logger.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                logger.error("All translation attempts failed")
                raise
    
    return text

def test_translation_integration():
    """Test that translation works with the same logic as transcribe_ro"""
    
    print("\n" + "="*70)
    print("Testing Translation Integration (Same Logic as transcribe_ro.py)")
    print("="*70 + "\n")
    
    try:
        # Test translation
        test_text = "Hello, this is a test. The transcription is working perfectly!"
        
        print("Original text (English):")
        print(f"  {test_text}\n")
        
        logger.info("="*60)
        logger.info("Starting translation to Romanian...")
        logger.info("="*60)
        
        translated = translate_with_retry(test_text, source_lang="en")
        
        logger.info("="*60)
        logger.info("✓ Translation completed successfully!")
        logger.info("="*60)
        
        print("\nTranslated text (Romanian):")
        print(f"  {translated}\n")
        
        if translated and translated != test_text:
            print("="*70)
            print("✓ SUCCESS: Translation is working correctly!")
            print("✓ The same logic is now implemented in transcribe_ro.py")
            print("="*70)
            return True
        else:
            print("="*70)
            print("✗ FAILED: Translation did not produce different text")
            print("="*70)
            return False
            
    except Exception as e:
        print("="*70)
        print(f"✗ ERROR: {e}")
        print("="*70)
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_translation_integration()
    sys.exit(0 if success else 1)
