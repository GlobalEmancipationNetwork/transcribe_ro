#!/usr/bin/env python3
"""
Test script to verify translation functionality is working
"""

import sys
import logging
from deep_translator import GoogleTranslator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def test_translation():
    """Test basic translation functionality"""
    
    test_cases = [
        ("Hello, how are you?", "en"),
        ("This is a test of the translation system.", "en"),
        ("The quick brown fox jumps over the lazy dog.", "en"),
    ]
    
    logger.info("="*60)
    logger.info("Testing deep-translator functionality")
    logger.info("="*60)
    
    for text, source_lang in test_cases:
        logger.info(f"\nOriginal ({source_lang}): {text}")
        
        try:
            translator = GoogleTranslator(source=source_lang, target='ro')
            translated = translator.translate(text)
            
            if translated and translated.strip():
                logger.info(f"✓ Translated (ro): {translated}")
                logger.info("✓ Translation successful!")
            else:
                logger.error("✗ Translation returned empty result")
                return False
                
        except Exception as e:
            logger.error(f"✗ Translation failed: {e}")
            return False
    
    logger.info("\n" + "="*60)
    logger.info("✓ All translation tests passed!")
    logger.info("="*60)
    return True

if __name__ == "__main__":
    success = test_translation()
    sys.exit(0 if success else 1)
