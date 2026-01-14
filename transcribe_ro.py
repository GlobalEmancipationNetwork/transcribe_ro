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
import time
import logging
from datetime import datetime
from pathlib import Path
import warnings
import glob

# Set MPS-specific environment variables for stability
# These help prevent NaN issues on Apple Silicon GPUs
os.environ['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'
os.environ['PYTORCH_MPS_HIGH_WATERMARK_RATIO'] = '0.0'

# IMPORTANT: Set environment variables to bypass torchcodec/AudioDecoder issues in pyannote.audio 4.x
# These must be set BEFORE importing pyannote.audio
os.environ['PYANNOTE_AUDIO_USE_TORCHAUDIO'] = '1'
os.environ['PYANNOTE_USE_TORCHAUDIO'] = '1'

# Global debug flag
DEBUG_MODE = False

# Configure logging with console handler
def setup_logging(debug=False):
    """Setup logging configuration."""
    global DEBUG_MODE
    DEBUG_MODE = debug
    
    # Remove existing handlers
    logger = logging.getLogger(__name__)
    logger.handlers.clear()
    
    # Console handler for all output
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if debug else logging.INFO)
    
    # Detailed format for debug mode
    if debug:
        formatter = logging.Formatter(
            '%(asctime)s.%(msecs)03d [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    
    return logger

# Initialize logger (will be configured by setup_logging in main())
logger = logging.getLogger(__name__)

# Default logging configuration (for when module is imported)
if not logger.handlers:
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    logger.setLevel(logging.INFO)

# Suppress warnings for cleaner output (unless debug mode)
warnings.filterwarnings('ignore')

try:
    import whisper
    from whisper.utils import get_writer
    logger.info(f"OpenAI Whisper loaded successfully (version: {getattr(whisper, '__version__', 'unknown')})")
except ImportError as e:
    # Show the ACTUAL error, not a generic message
    error_msg = str(e)
    logger.error(f"Failed to import whisper: {error_msg}")
    logger.error(f"Error type: {type(e).__name__}")
    
    # Check if it's truly whisper not installed vs a dependency issue
    if "whisper" in error_msg.lower() or "No module named 'whisper'" in error_msg:
        logger.error("OpenAI Whisper not installed. Please run: pip install openai-whisper")
    else:
        logger.error(f"Whisper import failed due to a dependency error: {error_msg}")
        logger.error("This might be a dependency conflict. Try:")
        logger.error("  1. pip uninstall whisper openai-whisper")
        logger.error("  2. pip install openai-whisper")
    
    # Log additional debug info
    logger.error(f"Python version: {sys.version}")
    logger.error(f"Python path: {sys.executable}")
    sys.exit(1)
except Exception as e:
    # Catch any other unexpected errors during import
    logger.error(f"Unexpected error importing whisper: {type(e).__name__}: {e}")
    import traceback
    logger.error(f"Traceback:\n{traceback.format_exc()}")
    sys.exit(1)

try:
    from deep_translator import GoogleTranslator
    ONLINE_TRANSLATOR_AVAILABLE = True
    logger.info("Translation service (deep-translator) loaded successfully")
except ImportError:
    logger.warning("deep-translator not installed. Online translation will not be available.")
    logger.warning("Install with: pip install deep-translator")
    ONLINE_TRANSLATOR_AVAILABLE = False
    GoogleTranslator = None

# Try to import offline translation dependencies
try:
    from transformers import MarianMTModel, MarianTokenizer
    import sentencepiece
    OFFLINE_TRANSLATOR_AVAILABLE = True
    logger.info("Offline translation (transformers) loaded successfully")
except ImportError:
    logger.warning("transformers not installed. Offline translation will not be available.")
    logger.warning("Install with: pip install transformers sentencepiece")
    OFFLINE_TRANSLATOR_AVAILABLE = False
    MarianMTModel = None
    MarianTokenizer = None

# Combined translator availability
TRANSLATOR_AVAILABLE = ONLINE_TRANSLATOR_AVAILABLE or OFFLINE_TRANSLATOR_AVAILABLE

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    logger.warning("PyTorch not available. Using basic device detection.")
    TORCH_AVAILABLE = False
    torch = None

# Try to import speaker diarization dependencies
DIARIZATION_IMPORT_ERROR = None
try:
    from pyannote.audio import Pipeline
    DIARIZATION_AVAILABLE = True
    logger.info("Speaker diarization (pyannote.audio community-1 model) loaded successfully")
except ImportError as e:
    logger.warning("pyannote.audio not installed. Speaker diarization will not be available.")
    logger.warning("Install with: pip install pyannote.audio")
    DIARIZATION_AVAILABLE = False
    DIARIZATION_IMPORT_ERROR = str(e)
    Pipeline = None
except NameError as e:
    # Handle AudioDecoder not defined error from torchcodec incompatibility
    error_str = str(e)
    if 'AudioDecoder' in error_str:
        logger.warning("pyannote.audio has torchcodec compatibility issues.")
        logger.warning("Speaker diarization import failed due to AudioDecoder error.")
        logger.warning("FIX: Run 'pip uninstall torchcodec' to resolve this issue.")
        DIARIZATION_IMPORT_ERROR = f"AudioDecoder compatibility: {error_str}"
    else:
        logger.warning(f"pyannote.audio import failed: {e}")
        DIARIZATION_IMPORT_ERROR = error_str
    DIARIZATION_AVAILABLE = False
    Pipeline = None
except Exception as e:
    # Catch any other import errors
    error_str = str(e)
    if 'AudioDecoder' in error_str:
        logger.warning("pyannote.audio has torchcodec compatibility issues.")
        logger.warning("FIX: Run 'pip uninstall torchcodec' to resolve this issue.")
        DIARIZATION_IMPORT_ERROR = f"AudioDecoder compatibility: {error_str}"
    else:
        logger.warning(f"pyannote.audio import error: {e}")
        DIARIZATION_IMPORT_ERROR = error_str
    DIARIZATION_AVAILABLE = False
    Pipeline = None


# =============================================================================
# VIDEO SUPPORT - Extract audio from video files using ffmpeg
# =============================================================================

# Supported video formats
VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v', 
                    '.mpeg', '.mpg', '.3gp', '.3g2', '.ts', '.mts', '.m2ts', '.vob'}

# Supported audio formats
AUDIO_EXTENSIONS = {'.mp3', '.wav', '.m4a', '.flac', '.ogg', '.wma', '.aac', '.opus',
                    '.aiff', '.aif', '.ape', '.wv', '.mka'}

def is_video_file(file_path):
    """Check if a file is a video file based on its extension."""
    return Path(file_path).suffix.lower() in VIDEO_EXTENSIONS

def is_audio_file(file_path):
    """Check if a file is an audio file based on its extension."""
    return Path(file_path).suffix.lower() in AUDIO_EXTENSIONS

def extract_audio_from_video(video_path, output_path=None, debug=False):
    """
    Extract audio from a video file using ffmpeg.
    
    Args:
        video_path: Path to the video file
        output_path: Optional output path for the extracted audio (defaults to temp file)
        debug: Enable debug logging
    
    Returns:
        tuple: (audio_path, is_temporary) - path to extracted audio and whether it's a temp file
    """
    import subprocess
    import tempfile
    
    video_path = Path(video_path)
    
    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")
    
    # Check if ffmpeg is available
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
    except (subprocess.SubprocessError, FileNotFoundError):
        raise RuntimeError(
            "ffmpeg is not installed or not in PATH.\n"
            "Please install ffmpeg:\n"
            "  - macOS: brew install ffmpeg\n"
            "  - Ubuntu/Debian: sudo apt install ffmpeg\n"
            "  - Windows: Download from https://ffmpeg.org/download.html"
        )
    
    # Determine output path
    is_temporary = output_path is None
    if is_temporary:
        # Create temp file with .wav extension (most compatible)
        temp_fd, output_path = tempfile.mkstemp(suffix='.wav', prefix='transcribe_ro_')
        os.close(temp_fd)
    
    output_path = Path(output_path)
    
    if debug:
        logger.debug(f"Extracting audio from video: {video_path}")
        logger.debug(f"Output audio path: {output_path}")
    
    try:
        # Extract audio using ffmpeg
        # -i: input file
        # -vn: no video
        # -acodec pcm_s16le: 16-bit PCM audio (WAV format)
        # -ar 16000: 16kHz sample rate (optimal for Whisper)
        # -ac 1: mono channel
        # -y: overwrite output file
        cmd = [
            'ffmpeg',
            '-i', str(video_path),
            '-vn',  # No video
            '-acodec', 'pcm_s16le',  # 16-bit PCM
            '-ar', '16000',  # 16kHz sample rate
            '-ac', '1',  # Mono
            '-y',  # Overwrite
            str(output_path)
        ]
        
        if debug:
            logger.debug(f"Running: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            error_msg = result.stderr[:500] if result.stderr else "Unknown ffmpeg error"
            raise RuntimeError(f"ffmpeg failed: {error_msg}")
        
        if not output_path.exists():
            raise RuntimeError(f"ffmpeg did not create output file: {output_path}")
        
        logger.info(f"✓ Audio extracted from video: {video_path.name}")
        
        return str(output_path), is_temporary
        
    except Exception as e:
        # Clean up temp file on error
        if is_temporary and output_path.exists():
            try:
                os.remove(output_path)
            except:
                pass
        raise


def check_internet_connectivity(timeout=3):
    """
    Check if internet connection is available.
    
    Args:
        timeout: Connection timeout in seconds
    
    Returns:
        bool: True if internet is available, False otherwise
    """
    try:
        import socket
        # Try to connect to Google's DNS server
        socket.create_connection(("8.8.8.8", 53), timeout=timeout)
        return True
    except (socket.error, OSError):
        return False


def get_marian_model_name(source_lang, target_lang='ro'):
    """
    Get the appropriate MarianMT model name for language translation.
    
    Args:
        source_lang: Source language code (ISO 639-1)
        target_lang: Target language code (default: 'ro' for Romanian)
    
    Returns:
        str: Model name or None if not available
    """
    # Map language codes to MarianMT model names
    # Helsinki-NLP provides models for many language pairs
    lang_map = {
        'en': 'opus-mt-en-roa',  # English to Romance languages (includes Romanian)
        'es': 'opus-mt-es-ro',    # Spanish to Romanian
        'fr': 'opus-mt-fr-ro',    # French to Romanian
        'de': 'opus-mt-de-ro',    # German to Romanian
        'it': 'opus-mt-it-ro',    # Italian to Romanian
        'pt': 'opus-mt-itc-itc',  # Portuguese (Italic to Italic, includes Romanian)
        'ru': 'opus-mt-ru-ro',    # Russian to Romanian
        'zh': 'opus-mt-zh-ro',    # Chinese to Romanian
        'ja': 'opus-mt-jap-ro',   # Japanese to Romanian
        'ar': 'opus-mt-ar-ro',    # Arabic to Romanian
        'hi': 'opus-mt-hi-ro',    # Hindi to Romanian
        'nl': 'opus-mt-nl-ro',    # Dutch to Romanian
        'pl': 'opus-mt-pl-ro',    # Polish to Romanian
        'tr': 'opus-mt-tr-ro',    # Turkish to Romanian
    }
    
    # For generic multi-language support, use the multi-language model
    if source_lang not in lang_map:
        # Try using the multilingual model as fallback
        return 'opus-mt-mul-en'  # Multi to English, then need second step
    
    return lang_map.get(source_lang)


class OfflineTranslator:
    """Offline translation using MarianMT models from transformers."""
    
    def __init__(self, cache_dir=None, debug=False):
        """
        Initialize offline translator.
        
        Args:
            cache_dir: Directory to cache models (default: ~/.cache/huggingface)
            debug: Enable debug output
        """
        self.cache_dir = cache_dir or os.path.expanduser("~/.cache/huggingface/hub")
        self.debug = debug
        self.models = {}  # Cache loaded models
        self.tokenizers = {}  # Cache loaded tokenizers
        
        if debug:
            logger.debug(f"OfflineTranslator initialized with cache_dir: {self.cache_dir}")
    
    def translate(self, text, source_lang='en', target_lang='ro', max_retries=1):
        """
        Translate text using offline MarianMT model.
        
        Args:
            text: Text to translate
            source_lang: Source language code
            target_lang: Target language code (default: 'ro')
            max_retries: Number of retry attempts
        
        Returns:
            Translated text or original text if translation fails
        """
        if not text or not text.strip():
            return text
        
        # Get model name for this language pair
        model_name = get_marian_model_name(source_lang, target_lang)
        
        if not model_name:
            logger.warning(f"No offline model available for {source_lang} -> {target_lang}")
            return text
        
        full_model_name = f"Helsinki-NLP/{model_name}"
        
        if self.debug:
            logger.debug(f"Using offline model: {full_model_name}")
            logger.debug(f"Text length: {len(text)} characters")
        
        try:
            # Load model and tokenizer (cached if already loaded)
            if full_model_name not in self.models:
                if self.debug:
                    logger.debug(f"Loading model {full_model_name}...")
                    load_start = time.time()
                
                logger.info(f"Loading offline translation model: {model_name}...")
                self.tokenizers[full_model_name] = MarianTokenizer.from_pretrained(
                    full_model_name,
                    cache_dir=self.cache_dir
                )
                self.models[full_model_name] = MarianMTModel.from_pretrained(
                    full_model_name,
                    cache_dir=self.cache_dir
                )
                
                if self.debug:
                    load_time = time.time() - load_start
                    logger.debug(f"Model loaded in {load_time:.2f} seconds")
                
                logger.info("✓ Model loaded successfully")
            
            model = self.models[full_model_name]
            tokenizer = self.tokenizers[full_model_name]
            
            # Translate text
            if self.debug:
                logger.debug("Tokenizing input...")
                translate_start = time.time()
            
            # Split into chunks if needed (MarianMT has token limits)
            max_length = 512
            if len(text) > 2000:  # Rough estimate for characters
                return self._translate_long_text(text, model, tokenizer)
            
            # Tokenize
            inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=max_length)
            
            if self.debug:
                logger.debug(f"Input tokens: {inputs['input_ids'].shape}")
            
            # Generate translation
            translated_tokens = model.generate(**inputs)
            
            # Decode
            translated_text = tokenizer.decode(translated_tokens[0], skip_special_tokens=True)
            
            if self.debug:
                translate_time = time.time() - translate_start
                logger.debug(f"Translation completed in {translate_time:.2f} seconds")
                logger.debug(f"Result length: {len(translated_text)} characters")
            
            return translated_text
            
        except Exception as e:
            logger.error(f"Offline translation failed: {e}")
            if self.debug:
                import traceback
                logger.debug("Full traceback:")
                logger.debug(traceback.format_exc())
            return text
    
    def _translate_long_text(self, text, model, tokenizer):
        """
        Translate long text by splitting into sentences.
        
        Args:
            text: Long text to translate
            model: Loaded MarianMT model
            tokenizer: Loaded MarianTokenizer
        
        Returns:
            Translated text
        """
        if self.debug:
            logger.debug("Text is long, splitting into sentences...")
        
        # Split by sentences
        sentences = text.replace('! ', '!|').replace('? ', '?|').replace('. ', '.|').split('|')
        translated_sentences = []
        
        for i, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if not sentence:
                continue
            
            if self.debug:
                logger.debug(f"Translating sentence {i+1}/{len(sentences)}...")
            
            try:
                inputs = tokenizer(sentence, return_tensors="pt", padding=True, truncation=True, max_length=512)
                translated_tokens = model.generate(**inputs)
                translated = tokenizer.decode(translated_tokens[0], skip_special_tokens=True)
                translated_sentences.append(translated)
            except Exception as e:
                logger.warning(f"Failed to translate sentence {i+1}: {e}")
                translated_sentences.append(sentence)  # Keep original
        
        return " ".join(translated_sentences)


def preload_model(model_name, debug=False):
    """
    Preload/download Whisper model to ensure it's available for use.
    This is helpful for first-time runs to download the model before processing.
    
    Args:
        model_name: Whisper model to preload
        debug: Enable debug output
    
    Returns:
        bool: True if model is available, False otherwise
    """
    try:
        import whisper
        model_path = whisper._download(whisper._MODELS[model_name])
        if debug:
            logger.debug(f"Model '{model_name}' is available at: {model_path}")
        return True
    except Exception as e:
        logger.warning(f"Could not preload model '{model_name}': {e}")
        return False


def check_diarization_requirements():
    """
    Check if speaker diarization requirements are met.
    
    Returns:
        tuple: (is_available, error_message)
            - is_available: True if diarization can be performed
            - error_message: None if available, otherwise descriptive error string
    """
    if not DIARIZATION_AVAILABLE:
        if DIARIZATION_IMPORT_ERROR and 'AudioDecoder' in DIARIZATION_IMPORT_ERROR:
            return False, ("torchcodec/AudioDecoder compatibility issue detected. "
                          "FIX: Run 'pip uninstall torchcodec' then restart the application.")
        elif DIARIZATION_IMPORT_ERROR:
            return False, f"pyannote.audio import error: {DIARIZATION_IMPORT_ERROR}"
        return False, "pyannote.audio not installed. Install with: pip install pyannote.audio"
    
    hf_token = os.environ.get('HF_TOKEN') or os.environ.get('HUGGING_FACE_TOKEN')
    if not hf_token:
        return False, "HF_TOKEN environment variable not set. Get your token at: https://huggingface.co/settings/tokens"
    
    return True, None


def perform_speaker_diarization(audio_path, speaker_names=None, debug=False):
    """
    Perform speaker diarization on an audio file.
    
    Args:
        audio_path: Path to audio file
        speaker_names: List of two speaker names (e.g., ["John", "Mary"])
        debug: Enable debug output
    
    Returns:
        tuple: (speaker_timeline, status_message)
            - speaker_timeline: Dictionary mapping time ranges to speaker labels, or None if failed
            - status_message: String describing the result or error
    """
    if debug:
        logger.debug("="*80)
        logger.debug("SPEAKER DIARIZATION START")
        logger.debug("="*80)
        logger.debug(f"Audio path: {audio_path}")
        logger.debug(f"Speaker names: {speaker_names}")
    
    # Check requirements first
    is_available, error_msg = check_diarization_requirements()
    if not is_available:
        logger.error(f"Speaker diarization unavailable: {error_msg}")
        if debug:
            logger.debug(f"DIARIZATION_AVAILABLE: {DIARIZATION_AVAILABLE}")
            hf_token = os.environ.get('HF_TOKEN') or os.environ.get('HUGGING_FACE_TOKEN')
            logger.debug(f"HF_TOKEN present: {bool(hf_token)}")
        return None, error_msg
    
    try:
        logger.info("Performing speaker diarization...")
        if debug:
            logger.debug("Loading pyannote speaker-diarization-community-1 model...")
            import time
            start_time = time.time()
        
        hf_token = os.environ.get('HF_TOKEN') or os.environ.get('HUGGING_FACE_TOKEN')
        
        # Load diarization pipeline (using community-1 model - recommended open-source model)
        # Handle API compatibility: pyannote.audio v3.1+ uses 'token', older versions use 'use_auth_token'
        pipeline = None
        try:
            # Try new API first (pyannote.audio v3.1+)
            pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-community-1",
                token=hf_token
            )
            if debug:
                logger.debug("Loaded diarization pipeline using new API (token parameter)")
        except TypeError as e:
            if "use_auth_token" in str(e) or "unexpected keyword argument" in str(e):
                # Fall back to old API (pyannote.audio v3.0 and earlier)
                pipeline = Pipeline.from_pretrained(
                    "pyannote/speaker-diarization-community-1",
                    use_auth_token=hf_token
                )
                if debug:
                    logger.debug("Loaded diarization pipeline using old API (use_auth_token parameter)")
            else:
                raise
        except NameError as e:
            # Handle AudioDecoder not defined error from torchcodec incompatibility
            error_str = str(e)
            if 'AudioDecoder' in error_str:
                error_msg = ("Speaker diarization failed due to torchcodec/AudioDecoder incompatibility.\n"
                           "FIX: Run 'pip uninstall torchcodec' in your terminal, then restart the application.\n"
                           "This is a known issue with pyannote.audio 4.x and torchcodec.")
                logger.error(error_msg)
                return None, error_msg
            raise
        
        if debug:
            logger.debug(f"Model loaded in {time.time() - start_time:.2f}s")
            logger.debug("Running diarization pipeline...")
            start_time = time.time()
        
        # Pre-load audio using librosa/soundfile to AVOID torchcodec/AudioDecoder issues in pyannote.audio 4.x
        # This is the FIX for the "torchcodec/AudioDecoder incompatibility" error
        # The pipeline accepts a dictionary with "waveform" and "sample_rate" keys
        audio_input = None
        try:
            # Method 1: Use librosa (most reliable, avoids torchcodec entirely)
            try:
                import librosa
                import numpy as np
                
                # Load audio with librosa at 16kHz (pyannote preferred sample rate)
                audio_data, sample_rate = librosa.load(audio_path, sr=16000, mono=True)
                
                # Convert to torch tensor with correct shape [channels, samples]
                waveform = torch.from_numpy(audio_data).unsqueeze(0).float()
                audio_input = {"waveform": waveform, "sample_rate": sample_rate}
                
                if debug:
                    logger.debug(f"Audio loaded via librosa: {waveform.shape}, {sample_rate}Hz")
            except ImportError:
                if debug:
                    logger.debug("librosa not available, trying soundfile...")
                raise
                
        except Exception as librosa_err:
            # Method 2: Use soundfile as fallback
            try:
                import soundfile as sf
                import numpy as np
                
                audio_data, sample_rate = sf.read(audio_path)
                
                # Handle stereo by averaging channels
                if len(audio_data.shape) > 1:
                    audio_data = np.mean(audio_data, axis=1)
                
                # Resample to 16kHz if needed
                if sample_rate != 16000:
                    try:
                        import librosa
                        audio_data = librosa.resample(audio_data, orig_sr=sample_rate, target_sr=16000)
                        sample_rate = 16000
                    except ImportError:
                        # If librosa not available for resampling, use scipy
                        try:
                            from scipy import signal
                            num_samples = int(len(audio_data) * 16000 / sample_rate)
                            audio_data = signal.resample(audio_data, num_samples)
                            sample_rate = 16000
                        except ImportError:
                            if debug:
                                logger.debug(f"Resampling not available, using original sample rate {sample_rate}Hz")
                
                waveform = torch.from_numpy(audio_data.astype(np.float32)).unsqueeze(0)
                audio_input = {"waveform": waveform, "sample_rate": sample_rate}
                
                if debug:
                    logger.debug(f"Audio loaded via soundfile: {waveform.shape}, {sample_rate}Hz")
                    
            except Exception as sf_err:
                if debug:
                    logger.debug(f"soundfile load failed ({sf_err}), falling back to file path")
                # Last resort: pass file path directly (may trigger torchcodec issues)
                audio_input = audio_path
        
        # Run diarization
        diarization = pipeline(audio_input)
        
        if debug:
            logger.debug(f"Diarization completed in {time.time() - start_time:.2f}s")
        
        # Map speaker labels to custom names if provided
        speaker_map = {}
        
        # Handle different pyannote.audio API versions
        # pyannote.audio 4.x returns DiarizeOutput which contains Annotation in .speaker_diarization
        # pyannote.audio 3.x returns Annotation directly with itertracks()
        # 
        # NOTE: If this function receives a DiarizeOutput object, it means the diarization
        # ran SUCCESSFULLY. This error is NOT due to audio quality - if audio quality was
        # the issue, diarization would fail earlier or return empty results. This is purely
        # an API compatibility issue with extracting segments from the output object.
        def get_diarization_segments(diarization_result):
            """Extract segments from diarization result, handling API differences.
            
            Returns an empty list on failure instead of raising, allowing transcription
            to continue without speaker labels.
            """
            segments = []
            extraction_attempts = []  # Track what we tried for debugging
            
            # === EXTENSIVE DEBUGGING ===
            obj_type = type(diarization_result).__name__
            logger.info(f"[DEBUG] Diarization output type: {obj_type}")
            logger.info(f"[DEBUG] Module: {type(diarization_result).__module__}")
            
            # Log ALL public attributes
            public_attrs = [attr for attr in dir(diarization_result) if not attr.startswith('_')]
            logger.info(f"[DEBUG] Public attributes: {public_attrs}")
            
            # Log private attributes too (might have useful data)
            private_attrs = [attr for attr in dir(diarization_result) if attr.startswith('_') and not attr.startswith('__')]
            logger.info(f"[DEBUG] Private attributes: {private_attrs}")
            
            # Try to log __dict__
            if hasattr(diarization_result, '__dict__'):
                try:
                    dict_keys = list(diarization_result.__dict__.keys())
                    logger.info(f"[DEBUG] __dict__ keys: {dict_keys}")
                    for key in dict_keys[:10]:  # First 10 keys
                        val = diarization_result.__dict__[key]
                        val_type = type(val).__name__
                        logger.info(f"[DEBUG]   {key}: type={val_type}")
                except Exception as e:
                    logger.info(f"[DEBUG] Could not inspect __dict__: {e}")
            
            # Try to get string representation
            try:
                str_repr = str(diarization_result)[:500]  # First 500 chars
                logger.info(f"[DEBUG] String repr: {str_repr}")
            except Exception as e:
                logger.info(f"[DEBUG] Could not get string repr: {e}")
            
            # Try to get repr
            try:
                repr_str = repr(diarization_result)[:500]
                logger.info(f"[DEBUG] Repr: {repr_str}")
            except Exception as e:
                logger.info(f"[DEBUG] Could not get repr: {e}")
            
            # === METHOD 1: pyannote.audio 4.x - speaker_diarization attribute ===
            if hasattr(diarization_result, 'speaker_diarization'):
                extraction_attempts.append('speaker_diarization')
                try:
                    annotation = diarization_result.speaker_diarization
                    logger.info(f"[DEBUG] speaker_diarization type: {type(annotation).__name__}")
                    logger.info(f"[DEBUG] speaker_diarization attrs: {[a for a in dir(annotation) if not a.startswith('_')][:20]}")
                    
                    if hasattr(annotation, 'itertracks'):
                        for turn, _, speaker in annotation.itertracks(yield_label=True):
                            segments.append((turn.start, turn.end, speaker))
                        if segments:
                            logger.info(f"[DEBUG] SUCCESS via speaker_diarization.itertracks(): {len(segments)} segments")
                            return segments
                    
                    # Try direct iteration on speaker_diarization
                    for turn, speaker in annotation:
                        segments.append((turn.start, turn.end, speaker))
                    if segments:
                        logger.info(f"[DEBUG] SUCCESS via speaker_diarization iteration: {len(segments)} segments")
                        return segments
                except Exception as e:
                    logger.info(f"[DEBUG] speaker_diarization extraction failed: {e}")
            
            # === METHOD 2: Direct itertracks (pyannote 3.x) ===
            if hasattr(diarization_result, 'itertracks'):
                extraction_attempts.append('itertracks')
                try:
                    for turn, _, speaker in diarization_result.itertracks(yield_label=True):
                        segments.append((turn.start, turn.end, speaker))
                    if segments:
                        logger.info(f"[DEBUG] SUCCESS via itertracks(): {len(segments)} segments")
                        return segments
                except Exception as e:
                    logger.info(f"[DEBUG] itertracks extraction failed: {e}")
            
            # === METHOD 3: to_annotation() method ===
            if hasattr(diarization_result, 'to_annotation'):
                extraction_attempts.append('to_annotation')
                try:
                    annotation = diarization_result.to_annotation()
                    logger.info(f"[DEBUG] to_annotation() returned: {type(annotation).__name__}")
                    for turn, _, speaker in annotation.itertracks(yield_label=True):
                        segments.append((turn.start, turn.end, speaker))
                    if segments:
                        logger.info(f"[DEBUG] SUCCESS via to_annotation(): {len(segments)} segments")
                        return segments
                except Exception as e:
                    logger.info(f"[DEBUG] to_annotation extraction failed: {e}")
            
            # === METHOD 4: Try common attribute names ===
            common_attrs = ['segments', 'tracks', 'labels', 'timeline', 'data', 'result', 
                           'output', 'annotation', 'diarization', 'speakers', 'turns']
            for attr_name in common_attrs:
                if hasattr(diarization_result, attr_name):
                    extraction_attempts.append(f'attr:{attr_name}')
                    try:
                        attr_val = getattr(diarization_result, attr_name)
                        logger.info(f"[DEBUG] Found .{attr_name}: type={type(attr_val).__name__}")
                        
                        # If it's iterable, try to extract
                        if hasattr(attr_val, '__iter__'):
                            for item in attr_val:
                                if isinstance(item, tuple) and len(item) >= 2:
                                    if hasattr(item[0], 'start'):
                                        turn = item[0]
                                        speaker = item[-1]
                                        segments.append((turn.start, turn.end, speaker))
                                elif hasattr(item, 'start') and hasattr(item, 'end'):
                                    label = getattr(item, 'label', getattr(item, 'speaker', 'SPEAKER'))
                                    segments.append((item.start, item.end, label))
                            if segments:
                                logger.info(f"[DEBUG] SUCCESS via .{attr_name}: {len(segments)} segments")
                                return segments
                        
                        # If it has itertracks
                        if hasattr(attr_val, 'itertracks'):
                            for turn, _, speaker in attr_val.itertracks(yield_label=True):
                                segments.append((turn.start, turn.end, speaker))
                            if segments:
                                logger.info(f"[DEBUG] SUCCESS via .{attr_name}.itertracks(): {len(segments)} segments")
                                return segments
                    except Exception as e:
                        logger.info(f"[DEBUG] .{attr_name} extraction failed: {e}")
            
            # === METHOD 5: Direct iteration ===
            extraction_attempts.append('direct_iteration')
            try:
                items_seen = 0
                for item in diarization_result:
                    items_seen += 1
                    if items_seen <= 3:
                        logger.info(f"[DEBUG] Iteration item {items_seen}: type={type(item).__name__}, value={str(item)[:100]}")
                    
                    if isinstance(item, tuple) and len(item) == 2:
                        turn, speaker = item
                        if hasattr(turn, 'start') and hasattr(turn, 'end'):
                            segments.append((turn.start, turn.end, speaker))
                    elif isinstance(item, tuple) and len(item) >= 3:
                        turn = item[0]
                        speaker = item[2] if len(item) > 2 else item[1]
                        if hasattr(turn, 'start') and hasattr(turn, 'end'):
                            segments.append((turn.start, turn.end, speaker))
                    elif hasattr(item, 'start') and hasattr(item, 'end'):
                        label = getattr(item, 'label', getattr(item, 'speaker', 'SPEAKER'))
                        segments.append((item.start, item.end, label))
                
                logger.info(f"[DEBUG] Direct iteration saw {items_seen} items, extracted {len(segments)} segments")
                if segments:
                    return segments
            except TypeError as e:
                logger.info(f"[DEBUG] Object is not iterable: {e}")
            except Exception as e:
                logger.info(f"[DEBUG] Direct iteration failed: {e}")
            
            # === METHOD 6: Internal data structures ===
            for timeline_attr in ['_timeline', '_tracks', '_segments']:
                for label_attr in ['_labels', '_speakers', '_tracks']:
                    if hasattr(diarization_result, timeline_attr) and hasattr(diarization_result, label_attr):
                        extraction_attempts.append(f'{timeline_attr}+{label_attr}')
                        try:
                            timeline = getattr(diarization_result, timeline_attr)
                            labels = getattr(diarization_result, label_attr)
                            logger.info(f"[DEBUG] Found {timeline_attr} ({type(timeline).__name__}) and {label_attr} ({type(labels).__name__})")
                            for seg, lbl in zip(timeline, labels):
                                if hasattr(seg, 'start'):
                                    segments.append((seg.start, seg.end, lbl))
                            if segments:
                                logger.info(f"[DEBUG] SUCCESS via {timeline_attr}+{label_attr}: {len(segments)} segments")
                                return segments
                        except Exception as e:
                            logger.info(f"[DEBUG] {timeline_attr}+{label_attr} extraction failed: {e}")
            
            # === METHOD 7: Try calling the object ===
            if callable(diarization_result):
                extraction_attempts.append('callable')
                try:
                    result = diarization_result()
                    logger.info(f"[DEBUG] Callable returned: {type(result).__name__}")
                except Exception as e:
                    logger.info(f"[DEBUG] Calling object failed: {e}")
            
            # === METHOD 8: Try dict-like access ===
            extraction_attempts.append('dict_access')
            try:
                if hasattr(diarization_result, 'keys'):
                    keys = list(diarization_result.keys())
                    logger.info(f"[DEBUG] Dict-like keys: {keys}")
                if hasattr(diarization_result, 'get'):
                    for key in ['segments', 'tracks', 'speakers', 'diarization']:
                        val = diarization_result.get(key)
                        if val:
                            logger.info(f"[DEBUG] .get('{key}'): {type(val).__name__}")
            except Exception as e:
                logger.info(f"[DEBUG] Dict-like access failed: {e}")
            
            # === GRACEFUL FALLBACK ===
            # Instead of raising an error, log comprehensive debug info and return empty list
            # This allows transcription to continue without speaker labels
            logger.warning(f"[DIARIZATION] Could not extract segments from {obj_type}.")
            logger.warning(f"[DIARIZATION] Extraction methods tried: {extraction_attempts}")
            logger.warning(f"[DIARIZATION] This is NOT an audio quality issue - diarization ran successfully.")
            logger.warning(f"[DIARIZATION] This is a pyannote.audio API compatibility issue.")
            logger.warning(f"[DIARIZATION] Transcription will continue without speaker labels.")
            
            # Return empty list for graceful degradation
            return []
        
        diarization_segments = get_diarization_segments(diarization)
        
        # Handle graceful fallback when segment extraction fails
        if not diarization_segments:
            status_msg = "Speaker diarization: extraction failed, continuing without speaker labels"
            logger.warning(status_msg)
            return None, status_msg
        
        # Order speakers by their FIRST appearance time in the audio (not alphabetically)
        # This ensures the first person to speak gets "Speaker 1", second gets "Speaker 2", etc.
        speaker_first_appearance = {}
        for start, end, speaker in diarization_segments:
            if speaker not in speaker_first_appearance:
                speaker_first_appearance[speaker] = start
        
        # Sort speakers by their first appearance time
        unique_speakers = sorted(speaker_first_appearance.keys(), key=lambda s: speaker_first_appearance[s])
        num_speakers_found = len(unique_speakers)
        
        if debug:
            logger.debug("Speaker first appearance times:")
            for spk in unique_speakers:
                logger.debug(f"  {spk}: {speaker_first_appearance[spk]:.2f}s")
        
        if debug:
            logger.debug(f"Unique speakers detected: {unique_speakers}")
            logger.debug(f"Number of speakers found: {num_speakers_found}")
        
        if speaker_names and len(speaker_names) >= 2:
            if num_speakers_found >= 2:
                speaker_map[unique_speakers[0]] = speaker_names[0]
                speaker_map[unique_speakers[1]] = speaker_names[1]
                logger.info(f"Mapping speakers: {unique_speakers[0]} -> {speaker_names[0]}, {unique_speakers[1]} -> {speaker_names[1]}")
            elif num_speakers_found == 1:
                speaker_map[unique_speakers[0]] = speaker_names[0]
                logger.warning(f"Only 1 speaker detected, mapping to: {speaker_names[0]}")
        
        # Convert to dictionary format
        speaker_timeline = {}
        for start, end, speaker in diarization_segments:
            mapped_speaker = speaker_map.get(speaker, speaker)
            speaker_timeline[(start, end)] = mapped_speaker
        
        num_segments = len(speaker_timeline)
        status_msg = f"Speaker diarization complete: {num_speakers_found} speakers, {num_segments} segments"
        logger.info(f"✓ {status_msg}")
        
        if debug:
            logger.debug(f"Speaker timeline entries: {num_segments}")
            logger.debug("First 5 entries:")
            for i, ((start, end), spk) in enumerate(list(speaker_timeline.items())[:5]):
                logger.debug(f"  [{start:.2f} -> {end:.2f}] {spk}")
        
        return speaker_timeline, status_msg
        
    except NameError as e:
        # Handle AudioDecoder not defined error from torchcodec incompatibility
        error_str = str(e)
        if 'AudioDecoder' in error_str:
            error_msg = ("Speaker diarization failed: torchcodec/AudioDecoder incompatibility.\n"
                        "FIX: Run 'pip uninstall torchcodec' then restart the application.")
        else:
            error_msg = f"Speaker diarization failed: {error_str}"
        logger.error(error_msg)
        if debug:
            import traceback
            logger.debug("Full traceback:")
            logger.debug(traceback.format_exc())
        return None, error_msg
    except Exception as e:
        error_str = str(e)
        # Check for AudioDecoder error in the exception message
        if 'AudioDecoder' in error_str:
            error_msg = ("Speaker diarization failed: torchcodec/AudioDecoder incompatibility.\n"
                        "FIX: Run 'pip uninstall torchcodec' then restart the application.")
        else:
            error_msg = f"Speaker diarization failed: {error_str}"
        logger.error(error_msg)
        if debug:
            import traceback
            logger.debug("Full traceback:")
            logger.debug(traceback.format_exc())
        return None, error_msg


def get_speaker_for_timestamp(speaker_timeline, timestamp):
    """
    Get the speaker label for a given timestamp.
    
    Args:
        speaker_timeline: Dictionary mapping time ranges to speakers
        timestamp: Time in seconds
    
    Returns:
        Speaker label or None
    """
    if not speaker_timeline:
        return None
    
    for (start, end), speaker in speaker_timeline.items():
        if start <= timestamp <= end:
            return speaker
    
    return None


def process_directory(directory_path, transcriber, args, supported_formats):
    """
    Process all audio/video files in a directory.
    
    Args:
        directory_path: Path to directory
        transcriber: AudioTranscriber instance
        args: Command-line arguments
        supported_formats: List of supported file extensions
    
    Returns:
        List of results for each processed file
    """
    directory = Path(directory_path)
    
    if not directory.exists() or not directory.is_dir():
        logger.error(f"Directory not found or not a directory: {directory_path}")
        return []
    
    # Find all supported files
    all_files = []
    for ext in supported_formats:
        all_files.extend(directory.glob(f"*{ext}"))
    
    if not all_files:
        logger.warning(f"No supported audio/video files found in: {directory_path}")
        logger.info(f"Supported formats: {', '.join(supported_formats)}")
        return []
    
    logger.info(f"Found {len(all_files)} files to process")
    
    results = []
    for i, file_path in enumerate(all_files, 1):
        logger.info("=" * 80)
        logger.info(f"Processing file {i}/{len(all_files)}: {file_path.name}")
        logger.info("=" * 80)
        
        try:
            # Process each file
            result = transcriber.process_audio(
                audio_path=str(file_path),
                output_path=args.output,
                translate=not args.no_translate,
                include_timestamps=not args.no_timestamps,
                output_format=args.format,
                speaker_names=args.speakers.split(',') if args.speakers else None
            )
            results.append({'file': str(file_path), 'status': 'success', 'result': result})
            logger.info(f"✓ Successfully processed: {file_path.name}")
            
        except Exception as e:
            logger.error(f"✗ Failed to process {file_path.name}: {e}")
            results.append({'file': str(file_path), 'status': 'failed', 'error': str(e)})
            
            if args.debug:
                import traceback
                logger.debug(traceback.format_exc())
        
        # Add spacing between files
        if i < len(all_files):
            print()
    
    # Summary
    successful = sum(1 for r in results if r['status'] == 'success')
    failed = len(results) - successful
    
    logger.info("=" * 80)
    logger.info("BATCH PROCESSING SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Total files: {len(results)}")
    logger.info(f"Successful: {successful}")
    logger.info(f"Failed: {failed}")
    logger.info("=" * 80)
    
    return results


def detect_device(preferred_device=None, debug=False):
    """
    Detect the best available compute device.
    
    Priority order:
    1. CUDA (NVIDIA GPU) if available
    2. MPS (Apple Silicon GPU) if available
    3. CPU as fallback
    
    Args:
        preferred_device: Optional device override ('cpu', 'mps', 'cuda', or 'auto')
        debug: Enable debug output
    
    Returns:
        tuple: (device_name, device_info_dict)
    """
    device_info = {
        'name': 'cpu',
        'type': 'CPU',
        'available': True,
        'reason': 'Default fallback device',
        'fp16_supported': False,
        'memory': None
    }
    
    # If user specified a device (and it's not 'auto'), try to honor it
    if preferred_device and preferred_device != 'auto':
        if debug:
            logger.debug(f"User requested device: {preferred_device}")
        
        # Validate the requested device
        if preferred_device == 'cpu':
            device_info['reason'] = 'User selected CPU'
            return 'cpu', device_info
        
        if not TORCH_AVAILABLE:
            logger.warning(f"PyTorch not available. Cannot use {preferred_device}. Falling back to CPU.")
            device_info['reason'] = 'PyTorch not available, using CPU'
            return 'cpu', device_info
        
        # Check CUDA
        if preferred_device == 'cuda':
            if torch.cuda.is_available():
                device_info.update({
                    'name': 'cuda',
                    'type': 'NVIDIA GPU (CUDA)',
                    'reason': 'User selected CUDA',
                    'fp16_supported': True,
                    'device_count': torch.cuda.device_count(),
                    'device_name': torch.cuda.get_device_name(0) if torch.cuda.device_count() > 0 else None,
                })
                try:
                    device_info['memory'] = f"{torch.cuda.get_device_properties(0).total_memory / (1024**3):.1f} GB"
                except:
                    pass
                return 'cuda', device_info
            else:
                logger.warning("CUDA requested but not available. Falling back to auto-detection.")
        
        # Check MPS
        if preferred_device == 'mps':
            if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                # Validate MPS works with a test operation
                mps_works = False
                try:
                    test_tensor = torch.zeros(1, device='mps')
                    test_result = test_tensor + 1
                    if hasattr(torch.mps, 'synchronize'):
                        torch.mps.synchronize()
                    if not torch.isnan(test_result).any():
                        mps_works = True
                except Exception as e:
                    logger.warning(f"MPS validation failed: {e}")
                
                if mps_works:
                    device_info.update({
                        'name': 'mps',
                        'type': 'Apple Silicon GPU (MPS)',
                        'reason': 'User selected MPS (validated)',
                        'fp16_supported': False,  # MPS works better with FP32
                        'note': 'Using FP32 for optimal performance on Apple Silicon (M1/M2/M3)',
                        'warning': 'MPS may encounter numerical instability. Auto-fallback to CPU is enabled.'
                    })
                    return 'mps', device_info
                else:
                    logger.warning("MPS requested but validation failed. Falling back to CPU.")
                    device_info['reason'] = 'MPS validation failed, using CPU'
                    return 'cpu', device_info
            else:
                logger.warning("MPS requested but not available. Falling back to auto-detection.")
    
    # Auto-detect best available device
    if debug:
        logger.debug("Auto-detecting best available device...")
    
    if not TORCH_AVAILABLE:
        device_info['reason'] = 'PyTorch not available, using CPU'
        return 'cpu', device_info
    
    # Check CUDA first (highest priority)
    if torch.cuda.is_available():
        if debug:
            logger.debug("CUDA is available")
        device_info.update({
            'name': 'cuda',
            'type': 'NVIDIA GPU (CUDA)',
            'reason': 'Best available GPU detected',
            'fp16_supported': True,
            'device_count': torch.cuda.device_count(),
            'device_name': torch.cuda.get_device_name(0) if torch.cuda.device_count() > 0 else None,
        })
        try:
            device_info['memory'] = f"{torch.cuda.get_device_properties(0).total_memory / (1024**3):.1f} GB"
        except:
            pass
        return 'cuda', device_info
    
    # Check MPS (Apple Silicon) - with validation test for M1/M2/M3 chips
    if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        if debug:
            logger.debug("MPS (Apple Silicon GPU) reported as available, running validation test...")
        
        # Validate MPS actually works with a test operation
        # This catches cases where MPS reports available but operations fail
        mps_works = False
        mps_error = None
        try:
            # Test basic tensor operations on MPS
            test_tensor = torch.zeros(1, device='mps')
            test_result = test_tensor + 1
            # Sync to ensure operation completes
            if hasattr(torch.mps, 'synchronize'):
                torch.mps.synchronize()
            # Verify result is correct (not NaN)
            if not torch.isnan(test_result).any():
                mps_works = True
                if debug:
                    logger.debug("MPS validation test PASSED")
            else:
                mps_error = "MPS returned NaN values"
                if debug:
                    logger.debug(f"MPS validation test FAILED: {mps_error}")
        except Exception as e:
            mps_error = str(e)
            if debug:
                logger.debug(f"MPS validation test FAILED with exception: {mps_error}")
        
        if mps_works:
            device_info.update({
                'name': 'mps',
                'type': 'Apple Silicon GPU (MPS)',
                'reason': 'Apple Silicon GPU detected and validated',
                'fp16_supported': False,  # MPS works better with FP32
                'note': 'Using FP32 for optimal performance on Apple Silicon (M1/M2/M3)',
                'warning': 'MPS may encounter numerical instability. Auto-fallback to CPU is enabled via PYTORCH_ENABLE_MPS_FALLBACK=1'
            })
            return 'mps', device_info
        else:
            logger.warning(f"MPS available but validation failed: {mps_error}")
            logger.warning("Falling back to CPU for stability")
            device_info['reason'] = f'MPS validation failed ({mps_error}), using CPU'
            device_info['mps_error'] = mps_error
            return 'cpu', device_info
    
    # Fallback to CPU
    if debug:
        logger.debug("No GPU detected, using CPU")
    device_info['reason'] = 'No GPU detected'
    return 'cpu', device_info


class AudioTranscriber:
    """Main class for audio transcription and translation."""
    
    def __init__(self, model_name="base", device="auto", verbose=True, debug=False, translation_mode="auto"):
        """
        Initialize the transcriber.
        
        Args:
            model_name: Whisper model to use (tiny, base, small, medium, large)
            device: Device to run on (auto, cpu, mps, or cuda)
            verbose: Enable verbose logging
            debug: Enable detailed debug output
            translation_mode: Translation mode (auto, online, offline)
        """
        self.model_name = model_name
        self.model = None
        self.verbose = verbose
        self.debug = debug
        self.translation_mode = translation_mode
        self.translator_available = TRANSLATOR_AVAILABLE
        self.online_translator_available = ONLINE_TRANSLATOR_AVAILABLE
        self.offline_translator_available = OFFLINE_TRANSLATOR_AVAILABLE
        self.offline_translator = None
        self.internet_available = None  # Will be checked when needed
        self.translation_status = "Unknown"  # Track current translation status
        
        # Initialize offline translator if available
        if self.offline_translator_available:
            try:
                self.offline_translator = OfflineTranslator(debug=debug)
            except Exception as e:
                logger.warning(f"Failed to initialize offline translator: {e}")
                self.offline_translator_available = False
        
        if not verbose:
            logger.setLevel(logging.WARNING)
        
        if self.debug:
            logger.debug("="*80)
            logger.debug("DEBUG MODE ENABLED - Detailed output will be shown")
            logger.debug("="*80)
            logger.debug(f"Model name: {model_name}")
            logger.debug(f"Requested device: {device}")
            logger.debug(f"Translator available: {self.translator_available}")
            logger.debug(f"Python version: {sys.version}")
            logger.debug(f"Working directory: {os.getcwd()}")
        
        # Detect and configure device
        detected_device, device_info = detect_device(preferred_device=device, debug=self.debug)
        self.device = detected_device
        self.device_info = device_info
        
        # Display device information
        logger.info("="*80)
        logger.info(f"🖥️  DEVICE CONFIGURATION")
        logger.info("="*80)
        logger.info(f"Selected Device: {device_info['type']}")
        logger.info(f"Reason: {device_info['reason']}")
        
        if device_info.get('device_name'):
            logger.info(f"GPU Model: {device_info['device_name']}")
        
        if device_info.get('memory'):
            logger.info(f"GPU Memory: {device_info['memory']}")
        
        if device_info.get('note'):
            logger.info(f"Note: {device_info['note']}")
        
        if device_info.get('warning'):
            logger.warning(f"⚠️  {device_info['warning']}")
        
        # Performance expectations
        if self.device == 'cuda':
            logger.info("⚡ GPU acceleration enabled - Expect 5-10x faster transcription")
            logger.info("💡 Using FP16 for optimal CUDA performance")
        elif self.device == 'mps':
            logger.info("⚡ Apple Silicon GPU acceleration enabled - Expect 3-5x faster transcription")
            logger.info("💡 Using FP32 for optimal Apple Silicon performance")
            logger.info("✓ FP16 warning eliminated - MPS configured correctly")
        else:
            logger.info("⚠️  Running on CPU - Consider using --device mps on Apple Silicon")
            logger.info("   or --device cuda on NVIDIA GPU for faster transcription")
        
        logger.info("="*80)
        
        if self.debug:
            logger.debug("="*80)
            logger.debug("DETAILED DEVICE INFO")
            logger.debug("="*80)
            for key, value in device_info.items():
                logger.debug(f"  {key}: {value}")
            logger.debug("="*80)
        
        logger.info(f"Loading Whisper model '{model_name}' on {self.device}...")
        
        if self.debug:
            start_time = time.time()
            logger.debug(f"Starting model load at {datetime.now().isoformat()}")
        
        try:
            # For MPS, we need to configure FP32 to avoid FP16 warning
            if self.device == 'mps':
                if self.debug:
                    logger.debug("Configuring model for MPS with FP32...")
                
                # Load model on CPU first, then move to MPS
                # This ensures proper FP32 configuration
                self.model = whisper.load_model(model_name, device='cpu')
                
                if TORCH_AVAILABLE and torch is not None:
                    # Convert model to FP32 explicitly
                    self.model = self.model.float()
                    # Move to MPS device
                    self.model = self.model.to('mps')
                    
                    if self.debug:
                        logger.debug("Model converted to FP32 and moved to MPS device")
            else:
                # For CUDA and CPU, use default loading
                self.model = whisper.load_model(model_name, device=self.device)
            
            if self.debug:
                load_time = time.time() - start_time
                logger.debug(f"Model loaded in {load_time:.2f} seconds")
                logger.debug(f"Model type: {type(self.model)}")
                if TORCH_AVAILABLE and torch is not None and hasattr(self.model, 'device'):
                    logger.debug(f"Model device: {self.model.device}")
            
            logger.info("✓ Model loaded successfully!")
            
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            if self.debug:
                import traceback
                logger.debug("Full traceback:")
                logger.debug(traceback.format_exc())
            
            # If MPS fails, try falling back to CPU
            if self.device == 'mps':
                logger.warning("MPS loading failed. Falling back to CPU...")
                try:
                    self.device = 'cpu'
                    self.model = whisper.load_model(model_name, device='cpu')
                    logger.info("✓ Model loaded successfully on CPU!")
                except Exception as e2:
                    logger.error(f"CPU fallback also failed: {e2}")
                    sys.exit(1)
            else:
                sys.exit(1)
    
    def _detect_nan_error(self, error_message):
        """
        Detect if an error is related to NaN values in MPS.
        
        Args:
            error_message: String representation of the error
        
        Returns:
            True if NaN error is detected, False otherwise
        """
        error_str = str(error_message).lower()
        
        # Check for explicit NaN value indicators (use word boundaries)
        import re
        nan_patterns = [
            r'\bnan\b',  # NaN as whole word
            r'invalid values.*tensor',  # invalid values with tensor
            r'found invalid values',  # found invalid values
        ]
        has_nan_pattern = any(re.search(pattern, error_str) for pattern in nan_patterns)
        
        # Check for constraint-related errors with "found invalid"
        constraint_with_invalid = (
            'independentconstraint' in error_str or 
            'categorical' in error_str
        ) and 'found invalid' in error_str
        
        # True if we have NaN pattern, or constraint error with "found invalid"
        return has_nan_pattern or constraint_with_invalid
    
    def transcribe_audio(self, audio_path, task="transcribe", retry_on_cpu=True):
        """
        Transcribe audio file using Whisper with automatic CPU fallback on NaN errors.
        
        Args:
            audio_path: Path to audio file
            task: 'transcribe' or 'translate' (translate translates to English in Whisper)
            retry_on_cpu: Whether to retry on CPU if MPS fails with NaN errors
        
        Returns:
            Dictionary containing transcription results
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        if self.debug:
            logger.debug("="*80)
            logger.debug("STEP: AUDIO TRANSCRIPTION")
            logger.debug("="*80)
            logger.debug(f"Audio file: {audio_path}")
            logger.debug(f"File size: {os.path.getsize(audio_path) / (1024*1024):.2f} MB")
            logger.debug(f"Task mode: {task}")
            logger.debug(f"Current device: {self.device}")
        
        logger.info(f"Transcribing: {audio_path}")
        logger.info("This may take a few minutes depending on the file size...")
        
        if self.debug:
            start_time = time.time()
            logger.debug(f"Transcription started at {datetime.now().isoformat()}")
        
        try:
            result = self.model.transcribe(
                audio_path,
                task=task,
                verbose=False
            )
            
            if self.debug:
                transcribe_time = time.time() - start_time
                logger.debug(f"Transcription completed in {transcribe_time:.2f} seconds")
                logger.debug(f"Result keys: {list(result.keys())}")
                logger.debug(f"Number of segments: {len(result.get('segments', []))}")
                logger.debug(f"Text length: {len(result.get('text', ''))}")
            
            logger.info("✓ Transcription completed successfully!")
            return result
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error during transcription: {error_msg}")
            
            if self.debug:
                import traceback
                logger.debug("Full traceback:")
                logger.debug(traceback.format_exc())
            
            # Check if this is a NaN error on MPS and we can retry on CPU
            if self.device == 'mps' and retry_on_cpu and self._detect_nan_error(error_msg):
                logger.warning("="*80)
                logger.warning("⚠️  MPS NaN ERROR DETECTED")
                logger.warning("="*80)
                logger.warning("This is a known issue with Whisper on Apple Silicon GPUs.")
                logger.warning("The model encountered numerical instability (NaN values).")
                logger.warning("Automatically falling back to CPU for stable transcription...")
                logger.warning("="*80)
                
                if self.debug:
                    logger.debug("Attempting CPU fallback...")
                    logger.debug("Reloading model on CPU device...")
                
                # Reload model on CPU
                try:
                    logger.info("Loading model on CPU device...")
                    self.model = whisper.load_model(self.model_name, device='cpu')
                    self.device = 'cpu'
                    logger.info("✓ Model successfully reloaded on CPU!")
                    logger.info("Retrying transcription on CPU...")
                    
                    if self.debug:
                        logger.debug("CPU fallback successful, retrying transcription...")
                        retry_start_time = time.time()
                    
                    # Retry transcription on CPU (without further retry to avoid infinite loop)
                    result = self.transcribe_audio(audio_path, task=task, retry_on_cpu=False)
                    
                    if self.debug:
                        retry_time = time.time() - retry_start_time
                        logger.debug(f"CPU retry completed in {retry_time:.2f} seconds")
                    
                    logger.info("="*80)
                    logger.info("✓ CPU FALLBACK SUCCESSFUL!")
                    logger.info("="*80)
                    logger.info("Transcription completed using CPU after MPS encountered errors.")
                    logger.info("Note: Future transcriptions in this session will use CPU.")
                    logger.info("="*80)
                    
                    return result
                    
                except Exception as cpu_error:
                    logger.error("="*80)
                    logger.error("❌ CPU FALLBACK FAILED")
                    logger.error("="*80)
                    logger.error(f"CPU fallback also failed: {cpu_error}")
                    if self.debug:
                        import traceback
                        logger.debug("CPU fallback traceback:")
                        logger.debug(traceback.format_exc())
                    raise Exception(f"Transcription failed on both MPS and CPU. Last error: {cpu_error}")
            
            # For other errors or if CPU fallback is disabled, raise the original error
            raise Exception(f"Error during transcription: {e}")
    
    def translate_to_romanian(self, text, source_lang="auto", max_retries=3):
        """
        Translate text to Romanian using online or offline translation with automatic fallback.
        
        Args:
            text: Text to translate
            source_lang: Source language code (default: auto-detect)
            max_retries: Maximum number of retry attempts for online translation
        
        Returns:
            Translated text
        """
        if self.debug:
            logger.debug("="*80)
            logger.debug("STEP: TRANSLATION TO ROMANIAN")
            logger.debug("="*80)
            logger.debug(f"Text length: {len(text)} characters")
            logger.debug(f"Source language: {source_lang}")
            logger.debug(f"Translation mode: {self.translation_mode}")
            logger.debug(f"Max retries: {max_retries}")
            logger.debug(f"Online translator available: {self.online_translator_available}")
            logger.debug(f"Offline translator available: {self.offline_translator_available}")
        
        if not self.translator_available:
            logger.error("="*80)
            logger.error("❌ NO TRANSLATION AVAILABLE")
            logger.error("="*80)
            logger.error("Neither online nor offline translation is available.")
            logger.error("Install dependencies:")
            logger.error("  Online:  pip install deep-translator")
            logger.error("  Offline: pip install transformers sentencepiece")
            logger.error("="*80)
            self.translation_status = "Failed - No translator available"
            if self.debug:
                logger.debug("REASON: No translation modules found")
            return text
        
        if not text or not text.strip():
            logger.warning("Empty text provided for translation")
            if self.debug:
                logger.debug(f"Text is empty or whitespace only: '{text}'")
            return text
        
        if self.debug:
            logger.debug(f"Text sample (first 200 chars): {text[:200]!r}")
        
        # Determine which translation method to use
        use_online = False
        use_offline = False
        
        if self.translation_mode == "online":
            # Force online translation
            if not self.online_translator_available:
                logger.error("Online translation requested but deep-translator not available!")
                logger.error("Install with: pip install deep-translator")
                self.translation_status = "Failed - Online translator not available"
                return text
            use_online = True
            if self.debug:
                logger.debug("DECISION: Using ONLINE translation (forced by mode)")
        
        elif self.translation_mode == "offline":
            # Force offline translation
            if not self.offline_translator_available:
                logger.error("Offline translation requested but transformers not available!")
                logger.error("Install with: pip install transformers sentencepiece")
                self.translation_status = "Failed - Offline translator not available"
                return text
            use_offline = True
            if self.debug:
                logger.debug("DECISION: Using OFFLINE translation (forced by mode)")
        
        else:  # auto mode
            # Check internet connectivity first
            if self.internet_available is None:
                logger.info("Checking internet connectivity...")
                self.internet_available = check_internet_connectivity()
                if self.debug:
                    logger.debug(f"Internet connectivity: {self.internet_available}")
            
            if self.internet_available and self.online_translator_available:
                use_online = True
                if self.debug:
                    logger.debug("DECISION: Using ONLINE translation (internet available)")
            elif self.offline_translator_available:
                use_offline = True
                logger.warning("No internet connection detected. Using OFFLINE translation.")
                if self.debug:
                    logger.debug("DECISION: Using OFFLINE translation (no internet)")
            elif self.online_translator_available:
                # Try online anyway even without confirmed internet
                use_online = True
                logger.warning("Internet status unknown. Attempting ONLINE translation...")
                if self.debug:
                    logger.debug("DECISION: Attempting ONLINE translation (internet check inconclusive)")
            else:
                logger.error("No translation method available!")
                self.translation_status = "Failed - No method available"
                return text
        
        # Execute translation
        if use_online:
            return self._translate_online(text, source_lang, max_retries)
        else:
            return self._translate_offline(text, source_lang)
    
    def _translate_online(self, text, source_lang, max_retries):
        """
        Translate using online service (deep-translator).
        
        Args:
            text: Text to translate
            source_lang: Source language code
            max_retries: Maximum retry attempts
        
        Returns:
            Translated text
        """
        if self.debug:
            logger.debug("="*80)
            logger.debug("ONLINE TRANSLATION METHOD")
            logger.debug("="*80)
        
        logger.info("🌐 Using ONLINE translation (Google Translate)")
        self.translation_status = "Online"
        
        # deep-translator has a 5000 character limit per request
        max_length = 4500  # Leave some buffer
        
        try:
            if len(text) <= max_length:
                if self.debug:
                    logger.debug(f"Text length ({len(text)}) is within limit ({max_length})")
                    logger.debug("Using single-chunk translation")
                return self._translate_with_retry(text, source_lang, max_retries)
            else:
                if self.debug:
                    logger.debug(f"Text length ({len(text)}) exceeds limit ({max_length})")
                    logger.debug("Using multi-chunk translation")
                logger.info(f"Text length ({len(text)} chars) exceeds limit. Splitting into chunks...")
                return self._translate_long_text(text, source_lang, max_retries)
        except Exception as e:
            error_msg = str(e).lower()
            
            # Check if it's a network error
            is_network_error = any(keyword in error_msg for keyword in [
                'connection', 'network', 'timeout', 'dns', 'resolve', 
                'unreachable', 'nodename', 'servname', 'errno 8'
            ])
            
            if is_network_error:
                logger.error(f"Network error during online translation: {e}")
                logger.error("Internet connection failed or service unavailable")
                
                # Try offline fallback if in auto mode and offline is available
                if self.translation_mode == "auto" and self.offline_translator_available:
                    logger.warning("="*80)
                    logger.warning("⚠️  AUTOMATIC FALLBACK TO OFFLINE TRANSLATION")
                    logger.warning("="*80)
                    logger.warning("Online translation failed due to network issues.")
                    logger.warning("Falling back to offline translation...")
                    logger.warning("="*80)
                    
                    if self.debug:
                        logger.debug("Attempting offline translation as fallback...")
                    
                    return self._translate_offline(text, source_lang)
                else:
                    logger.error("No fallback available. Returning original text.")
                    self.translation_status = "Failed - Network error"
                    return text
            else:
                logger.error(f"Online translation failed: {e}")
                logger.error("Returning original text")
                self.translation_status = "Failed - Translation error"
                if self.debug:
                    import traceback
                    logger.debug("Full traceback:")
                    logger.debug(traceback.format_exc())
                return text
    
    def _translate_offline(self, text, source_lang):
        """
        Translate using offline models (MarianMT).
        
        Args:
            text: Text to translate
            source_lang: Source language code
        
        Returns:
            Translated text
        """
        if self.debug:
            logger.debug("="*80)
            logger.debug("OFFLINE TRANSLATION METHOD")
            logger.debug("="*80)
        
        logger.info("💾 Using OFFLINE translation (MarianMT)")
        logger.info("Note: First time may take longer as model downloads...")
        self.translation_status = "Offline"
        
        try:
            # Use offline translator
            if source_lang == "auto":
                # Offline doesn't support auto-detect, try common languages
                logger.warning("Offline translation doesn't support auto-detection.")
                logger.warning("Assuming source language is English. Specify --source-lang if different.")
                source_lang = "en"
                if self.debug:
                    logger.debug("Auto-detection not available, using 'en' as source")
            
            translated = self.offline_translator.translate(text, source_lang=source_lang, target_lang='ro')
            
            if translated and translated != text:
                logger.info(f"✓ Offline translation successful! ({len(text)} -> {len(translated)} chars)")
                return translated
            else:
                logger.warning("Offline translation returned same text")
                return text
                
        except Exception as e:
            logger.error(f"Offline translation failed: {e}")
            self.translation_status = "Failed - Offline error"
            if self.debug:
                import traceback
                logger.debug("Full traceback:")
                logger.debug(traceback.format_exc())
            return text
    
    def _translate_with_retry(self, text, source_lang, max_retries):
        """
        Translate text with retry logic.
        
        Args:
            text: Text to translate
            source_lang: Source language code
            max_retries: Maximum number of retry attempts
        
        Returns:
            Translated text
        """
        if self.debug:
            logger.debug(f"_translate_with_retry called with {len(text)} chars")
            
        for attempt in range(max_retries):
            try:
                logger.info(f"Translation attempt {attempt + 1}/{max_retries}...")
                
                if self.debug:
                    logger.debug(f"Attempt {attempt + 1} started at {datetime.now().isoformat()}")
                    logger.debug(f"Source language: {source_lang}")
                    attempt_start = time.time()
                
                # Create translator instance for this request
                if source_lang == "auto" or source_lang == "en":
                    if self.debug:
                        logger.debug("Creating GoogleTranslator(source='auto', target='ro')")
                    translator = GoogleTranslator(source='auto', target='ro')
                else:
                    if self.debug:
                        logger.debug(f"Creating GoogleTranslator(source='{source_lang}', target='ro')")
                    translator = GoogleTranslator(source=source_lang, target='ro')
                
                if self.debug:
                    logger.debug(f"Calling translator.translate() with {len(text)} chars...")
                
                translated = translator.translate(text)
                
                if self.debug:
                    attempt_time = time.time() - attempt_start
                    logger.debug(f"Translation call completed in {attempt_time:.2f} seconds")
                    logger.debug(f"Result type: {type(translated)}")
                    logger.debug(f"Result length: {len(translated) if translated else 0}")
                
                if translated and translated.strip():
                    logger.info(f"✓ Translation successful! ({len(text)} -> {len(translated)} chars)")
                    
                    if self.debug:
                        logger.debug(f"Translation sample (first 200 chars): {translated[:200]!r}")
                        logger.debug(f"Original != Translated: {text != translated}")
                    
                    return translated
                else:
                    logger.warning("Translation returned empty result")
                    
                    if self.debug:
                        logger.debug(f"Empty result: translated='{translated}'")
                    
                    if attempt < max_retries - 1:
                        wait_time = 1 * (attempt + 1)
                        if self.debug:
                            logger.debug(f"Waiting {wait_time}s before retry")
                        time.sleep(wait_time)  # Exponential backoff
                        continue
                    return text
                    
            except Exception as e:
                logger.warning(f"Translation attempt {attempt + 1} failed: {str(e)}")
                
                if self.debug:
                    logger.debug(f"Exception type: {type(e).__name__}")
                    logger.debug(f"Exception details: {str(e)}")
                    import traceback
                    logger.debug("Full traceback:")
                    logger.debug(traceback.format_exc())
                
                if attempt < max_retries - 1:
                    wait_time = 2 * (attempt + 1)  # Exponential backoff: 2s, 4s, 6s
                    logger.info(f"Retrying in {wait_time} seconds...")
                    
                    if self.debug:
                        logger.debug(f"Sleeping for {wait_time} seconds before retry {attempt + 2}")
                    
                    time.sleep(wait_time)
                else:
                    logger.error("All translation attempts failed")
                    if self.debug:
                        logger.debug("No more retries available, raising exception")
                    raise
        
        return text
    
    def _translate_long_text(self, text, source_lang, max_retries):
        """
        Translate long text by splitting into manageable chunks.
        
        Args:
            text: Long text to translate
            source_lang: Source language code
            max_retries: Maximum number of retry attempts per chunk
        
        Returns:
            Translated text
        """
        max_length = 4500
        
        # Split by sentences first
        sentences = text.replace('! ', '!|').replace('? ', '?|').replace('. ', '.|').split('|')
        
        translated_chunks = []
        current_chunk = ""
        chunk_count = 0
        
        for i, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # Check if adding this sentence would exceed the limit
            if len(current_chunk) + len(sentence) + 1 < max_length:
                current_chunk += sentence + " "
            else:
                # Translate current chunk
                if current_chunk:
                    chunk_count += 1
                    logger.info(f"Translating chunk {chunk_count} ({len(current_chunk)} chars)...")
                    translated = self._translate_with_retry(current_chunk.strip(), source_lang, max_retries)
                    translated_chunks.append(translated)
                    time.sleep(0.5)  # Small delay between chunks
                
                current_chunk = sentence + " "
        
        # Translate remaining chunk
        if current_chunk:
            chunk_count += 1
            logger.info(f"Translating final chunk {chunk_count} ({len(current_chunk)} chars)...")
            translated = self._translate_with_retry(current_chunk.strip(), source_lang, max_retries)
            translated_chunks.append(translated)
        
        result = " ".join(translated_chunks)
        logger.info(f"✓ All {chunk_count} chunks translated successfully!")
        return result
    
    def process_audio(
        self,
        audio_path,
        output_path=None,
        translate=True,
        include_timestamps=True,
        output_format="txt",
        speaker_names=None
    ):
        """
        Process audio/video file: transcribe and optionally translate to Romanian.
        
        Supports both audio files and video files. Video files will have their audio
        extracted automatically using ffmpeg.
        
        Args:
            audio_path: Path to audio or video file
            output_path: Path for output file (default: same as input with .txt extension)
            translate: Whether to translate to Romanian
            include_timestamps: Whether to include timestamps in output
            output_format: Output format (txt, json, srt, vtt)
            speaker_names: List of two speaker names for diarization (e.g., ["John", "Mary"])
        
        Returns:
            Dictionary with processing results
        """
        # ============================================================
        # TIMING: Start overall timer and initialize timing dictionary
        # ============================================================
        process_start_time = time.time()
        timing_data = {
            'audio_extraction': 0.0,
            'transcription': 0.0,
            'speaker_diarization': 0.0,
            'translation': 0.0,
            'file_writing': 0.0,
        }
        
        def elapsed_str():
            """Return formatted elapsed time string from start."""
            elapsed = time.time() - process_start_time
            return f"[{elapsed:6.1f}s]"
        
        logger.info(f"{elapsed_str()} Starting processing: {Path(audio_path).name}")
        
        if self.debug:
            logger.debug("="*80)
            logger.debug("STEP: PROCESS AUDIO/VIDEO")
            logger.debug("="*80)
            logger.debug(f"Input path: {audio_path}")
            logger.debug(f"Output path: {output_path}")
            logger.debug(f"Translate: {translate}")
            logger.debug(f"Include timestamps: {include_timestamps}")
            logger.debug(f"Output format: {output_format}")
        
        # Check if input is a video file and extract audio if needed
        temp_audio_file = None
        original_input_path = audio_path  # Keep reference to original for output naming
        
        if is_video_file(audio_path):
            logger.info(f"{elapsed_str()} 🎬 Video file detected: {Path(audio_path).name}")
            logger.info(f"{elapsed_str()} 📤 Extracting audio from video...")
            extraction_start = time.time()
            try:
                audio_path, is_temp = extract_audio_from_video(audio_path, debug=self.debug)
                if is_temp:
                    temp_audio_file = audio_path  # Track temp file for cleanup
                timing_data['audio_extraction'] = time.time() - extraction_start
                logger.info(f"{elapsed_str()} ✓ Audio extracted ({timing_data['audio_extraction']:.1f}s)")
                if self.debug:
                    logger.debug(f"Extracted audio to: {audio_path}")
            except RuntimeError as e:
                logger.error(f"Failed to extract audio from video: {e}")
                return {
                    'error': str(e),
                    'original_path': str(original_input_path)
                }
        
        try:
            # Transcribe audio
            logger.info(f"{elapsed_str()} 🎤 Starting transcription (Whisper {self.model_name})...")
            transcribe_start = time.time()
            result = self.transcribe_audio(audio_path)
            timing_data['transcription'] = time.time() - transcribe_start
            logger.info(f"{elapsed_str()} ✓ Transcription complete ({timing_data['transcription']:.1f}s)")
        finally:
            # Clean up temporary audio file
            if temp_audio_file and os.path.exists(temp_audio_file):
                try:
                    os.remove(temp_audio_file)
                    if self.debug:
                        logger.debug(f"Cleaned up temp audio file: {temp_audio_file}")
                except Exception as cleanup_err:
                    logger.warning(f"Failed to clean up temp file: {cleanup_err}")
        
        # Extract information
        detected_language = result.get('language', 'unknown')
        transcribed_text = result.get('text', '').strip()
        segments = result.get('segments', [])
        
        # Perform speaker diarization if requested
        speaker_timeline = None
        if speaker_names and len(speaker_names) == 2:
            logger.info(f"{elapsed_str()} 👥 Starting speaker diarization...")
            diarization_start = time.time()
            speaker_timeline = perform_speaker_diarization(
                audio_path, 
                speaker_names=speaker_names, 
                debug=self.debug
            )
            timing_data['speaker_diarization'] = time.time() - diarization_start
            logger.info(f"{elapsed_str()} ✓ Diarization complete ({timing_data['speaker_diarization']:.1f}s)")
            
            # Add speaker labels to segments
            if speaker_timeline:
                for segment in segments:
                    segment_mid = (segment['start'] + segment['end']) / 2
                    speaker = get_speaker_for_timestamp(speaker_timeline, segment_mid)
                    segment['speaker'] = speaker if speaker else "Unknown"
        
        if self.debug:
            logger.debug("="*80)
            logger.debug("STEP: LANGUAGE DETECTION RESULTS")
            logger.debug("="*80)
            logger.debug(f"Detected language code: {detected_language}")
            logger.debug(f"Language name: {self._get_language_name(detected_language)}")
            
            # Check if language confidence is available
            if 'language_probability' in result:
                logger.debug(f"Language confidence: {result['language_probability']:.4f}")
            else:
                logger.debug("Language confidence: Not available in result")
            
            logger.debug(f"Number of segments: {len(segments)}")
            logger.debug(f"Total transcription length: {len(transcribed_text)} characters")
            logger.debug(f"Transcription sample (first 200 chars): {transcribed_text[:200]!r}")
        
        logger.info(f"{elapsed_str()} ✓ Detected language: {detected_language}")
        logger.info(f"{elapsed_str()} ✓ Transcription length: {len(transcribed_text)} characters")
        
        # Translate to Romanian if needed and requested
        translated_text = None
        
        if self.debug:
            logger.debug("="*80)
            logger.debug("STEP: TRANSLATION DECISION")
            logger.debug("="*80)
            logger.debug(f"Translate flag: {translate}")
            logger.debug(f"Detected language: {detected_language}")
            logger.debug(f"Is Romanian: {detected_language == 'ro'}")
        
        if translate and detected_language != 'ro':
            if self.debug:
                logger.debug("DECISION: Translation will be attempted")
                logger.debug(f"REASON: translate={translate} and detected_language='{detected_language}' != 'ro'")
            
            logger.info(f"{elapsed_str()} 🌍 Starting translation to Romanian...")
            
            translate_start = time.time()
            translated_text = self.translate_to_romanian(transcribed_text, source_lang=detected_language)
            timing_data['translation'] = time.time() - translate_start
            
            if translated_text and translated_text != transcribed_text:
                logger.info(f"{elapsed_str()} ✓ Translation complete ({timing_data['translation']:.1f}s)")
                
                if self.debug:
                    logger.debug(f"Translation changed the text: True")
                    logger.debug(f"Original length: {len(transcribed_text)}")
                    logger.debug(f"Translated length: {len(translated_text)}")
                    logger.debug(f"Translated sample (first 200 chars): {translated_text[:200]!r}")
            else:
                logger.warning(f"{elapsed_str()} Translation did not produce different text")
                
                if self.debug:
                    logger.debug(f"Translation result same as original: {translated_text == transcribed_text}")
                    logger.debug(f"Translation is None: {translated_text is None}")
                    logger.debug(f"Translation is empty: {not translated_text}")
                    
        elif detected_language == 'ro':
            if self.debug:
                logger.debug("DECISION: Translation skipped")
                logger.debug("REASON: Audio is already in Romanian")
            
            logger.info("Audio is already in Romanian. No translation needed.")
            translated_text = transcribed_text
            
        else:
            if self.debug:
                logger.debug("DECISION: Translation skipped")
                logger.debug("REASON: --no-translate flag was set")
            
            logger.info("Translation skipped (--no-translate flag)")
            translated_text = None
        
        # Prepare output paths
        if output_path is None:
            audio_name = Path(audio_path).stem
            output_path = Path(audio_path).parent / f"{audio_name}_transcription.{output_format}"
        else:
            output_path = Path(output_path)
        
        # Prepare translated output path if translation was performed
        translated_output_path = None
        if translated_text and translated_text != transcribed_text:
            # Create translated file path with "_translated_ro" suffix
            output_stem = output_path.stem
            # Remove "_transcription" suffix if present to avoid double suffixes
            if output_stem.endswith('_transcription'):
                output_stem = output_stem[:-14]  # Remove "_transcription"
            translated_output_path = output_path.parent / f"{output_stem}_translated_ro{output_path.suffix}"
        
        if self.debug:
            logger.debug("="*80)
            logger.debug("STEP: PREPARE OUTPUT")
            logger.debug("="*80)
            logger.debug(f"Original output path: {output_path}")
            logger.debug(f"Original output path (absolute): {output_path.absolute()}")
            if translated_output_path:
                logger.debug(f"Translated output path: {translated_output_path}")
                logger.debug(f"Translated output path (absolute): {translated_output_path.absolute()}")
            logger.debug(f"Output format: {output_format}")
            logger.debug(f"Output directory: {output_path.parent}")
            logger.debug(f"Output directory exists: {output_path.parent.exists()}")
        
        # Generate metadata
        metadata = {
            'source_file': str(audio_path),
            'detected_language': detected_language,
            'transcription_date': datetime.now().isoformat(),
            'model_used': self.model_name,
            'translation_applied': translate and detected_language != 'ro'
        }
        
        if self.debug:
            logger.debug("Metadata:")
            for key, value in metadata.items():
                logger.debug(f"  {key}: {value}")
        
        # Write original transcription output
        logger.info(f"{elapsed_str()} 📝 Writing output files...")
        write_start = time.time()
        
        if self.debug:
            logger.debug("="*80)
            logger.debug("STEP: WRITE ORIGINAL TRANSCRIPTION FILE")
            logger.debug("="*80)
            logger.debug(f"Writing to: {output_path}")
        
        try:
            if output_format == 'json':
                if self.debug:
                    logger.debug("Format: JSON")
                self._write_json_output(output_path, transcribed_text, None, segments, metadata)
            elif output_format in ['srt', 'vtt']:
                if self.debug:
                    logger.debug(f"Format: {output_format.upper()} subtitle")
                self._write_subtitle_output(output_path, segments, False, output_format)
            else:  # txt format
                if self.debug:
                    logger.debug("Format: Text")
                self._write_text_output(
                    output_path,
                    transcribed_text,
                    None,  # No translation in original file
                    segments if include_timestamps else None,
                    metadata
                )
            
            if self.debug:
                logger.debug(f"File size: {os.path.getsize(output_path) / 1024:.2f} KB")
                logger.debug(f"File exists: {output_path.exists()}")
            
            logger.info(f"{elapsed_str()} ✓ Original transcription saved to: {output_path}")
            
        except Exception as e:
            logger.error(f"Failed to write original transcription file: {e}")
            if self.debug:
                import traceback
                logger.debug("Full traceback:")
                logger.debug(traceback.format_exc())
            raise
        
        # Write translated output if translation was performed
        if translated_output_path:
            if self.debug:
                logger.debug("="*80)
                logger.debug("STEP: WRITE TRANSLATED FILE")
                logger.debug("="*80)
                logger.debug(f"Writing to: {translated_output_path}")
            
            try:
                # Update metadata for translated file
                translated_metadata = metadata.copy()
                translated_metadata['file_type'] = 'romanian_translation'
                translated_metadata['original_language'] = detected_language
                
                if output_format == 'json':
                    if self.debug:
                        logger.debug("Format: JSON")
                    self._write_json_output(translated_output_path, translated_text, None, segments, translated_metadata)
                elif output_format in ['srt', 'vtt']:
                    if self.debug:
                        logger.debug(f"Format: {output_format.upper()} subtitle")
                    # For subtitles, we need to translate segments
                    self._write_translated_subtitle_output(translated_output_path, segments, output_format)
                else:  # txt format
                    if self.debug:
                        logger.debug("Format: Text")
                    self._write_translated_text_output(
                        translated_output_path,
                        translated_text,
                        segments if include_timestamps else None,
                        translated_metadata
                    )
                
                if self.debug:
                    logger.debug(f"File size: {os.path.getsize(translated_output_path) / 1024:.2f} KB")
                    logger.debug(f"File exists: {translated_output_path.exists()}")
                
                logger.info(f"{elapsed_str()} ✓ Romanian translation saved to: {translated_output_path}")
                
            except Exception as e:
                logger.error(f"Failed to write translated file: {e}")
                if self.debug:
                    import traceback
                    logger.debug("Full traceback:")
                    logger.debug(traceback.format_exc())
                raise
        
        timing_data['file_writing'] = time.time() - write_start
        
        # ============================================================
        # TIMING SUMMARY TABLE
        # ============================================================
        total_time = time.time() - process_start_time
        
        # Build the summary table
        logger.info("")
        logger.info("=" * 60)
        logger.info("⏱️  PERFORMANCE SUMMARY")
        logger.info("=" * 60)
        logger.info(f"{'Step':<30} {'Time':>10} {'%':>8}")
        logger.info("-" * 60)
        
        # Only show steps that were actually performed (time > 0)
        steps_to_show = [
            ('Audio Extraction', timing_data['audio_extraction']),
            ('Transcription (Whisper)', timing_data['transcription']),
            ('Speaker Diarization', timing_data['speaker_diarization']),
            ('Translation', timing_data['translation']),
            ('File Writing', timing_data['file_writing']),
        ]
        
        for step_name, step_time in steps_to_show:
            if step_time > 0:
                percentage = (step_time / total_time) * 100 if total_time > 0 else 0
                logger.info(f"{step_name:<30} {step_time:>8.1f}s {percentage:>7.1f}%")
        
        logger.info("-" * 60)
        logger.info(f"{'TOTAL':<30} {total_time:>8.1f}s {100.0:>7.1f}%")
        logger.info("=" * 60)
        logger.info("")
        
        return {
            'output_file': str(output_path),
            'translated_output_file': str(translated_output_path) if translated_output_path else None,
            'detected_language': detected_language,
            'transcribed_text': transcribed_text,
            'translated_text': translated_text,
            'metadata': metadata,
            'timing': timing_data,
            'total_time': total_time
        }
    
    def _write_text_output(self, output_path, transcription, translation, segments, metadata):
        """Write transcription to text file (original language only)."""
        with open(output_path, 'w', encoding='utf-8') as f:
            # Write header
            f.write("="*80 + "\n")
            f.write("TRANSCRIPTION RESULTS (ORIGINAL LANGUAGE)\n")
            f.write("="*80 + "\n\n")
            
            # Write metadata
            f.write("METADATA:\n")
            f.write("-" * 40 + "\n")
            for key, value in metadata.items():
                f.write(f"{key.replace('_', ' ').title()}: {value}\n")
            f.write("\n")
            
            # Write original transcription
            f.write("TRANSCRIPTION:\n")
            f.write("-" * 40 + "\n")
            f.write(transcription + "\n\n")
            
            # Write timestamps if available
            if segments:
                f.write("TIMESTAMPS:\n")
                f.write("-" * 40 + "\n")
                for segment in segments:
                    start_time = self._format_timestamp(segment['start'])
                    end_time = self._format_timestamp(segment['end'])
                    text = segment['text'].strip()
                    speaker = segment.get('speaker')
                    if speaker:
                        f.write(f"[{start_time} -> {end_time}] [{speaker}] {text}\n")
                    else:
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
        """Write transcription to subtitle file (SRT or VTT) - original language."""
        logger.info(f"Generating {format_type.upper()} subtitle file...")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            if format_type == 'vtt':
                f.write("WEBVTT\n\n")
            
            for i, segment in enumerate(segments, 1):
                start_time = self._format_timestamp(segment['start'], format_type)
                end_time = self._format_timestamp(segment['end'], format_type)
                text = segment['text'].strip()
                speaker = segment.get('speaker')
                
                # Add speaker label if available
                if speaker:
                    text = f"[{speaker}] {text}"
                
                # Note: translate parameter is kept for backward compatibility but not used
                # Translation is now handled in separate file
                
                if format_type == 'srt':
                    f.write(f"{i}\n")
                    f.write(f"{start_time} --> {end_time}\n")
                    f.write(f"{text}\n\n")
                else:  # vtt
                    f.write(f"{start_time} --> {end_time}\n")
                    f.write(f"{text}\n\n")
        
        logger.info(f"✓ Subtitle file created with {len(segments)} segments")
    
    def _write_translated_text_output(self, output_path, translation, segments, metadata):
        """Write Romanian translation to text file with timestamped segments."""
        with open(output_path, 'w', encoding='utf-8') as f:
            # Write header
            f.write("="*80 + "\n")
            f.write("ROMANIAN TRANSLATION\n")
            f.write("="*80 + "\n\n")
            
            # Write metadata
            f.write("METADATA:\n")
            f.write("-" * 40 + "\n")
            for key, value in metadata.items():
                f.write(f"{key.replace('_', ' ').title()}: {value}\n")
            f.write("\n")
            
            # Write translated text
            f.write("TRANSLATED TEXT:\n")
            f.write("-" * 40 + "\n")
            f.write(translation + "\n\n")
            
            # Write timestamps with translated segments if available
            if segments and self.translator_available:
                f.write("TIMESTAMPS WITH TRANSLATED SEGMENTS:\n")
                f.write("-" * 40 + "\n")
                logger.info("Translating individual segments for timestamped output...")
                
                for i, segment in enumerate(segments, 1):
                    start_time = self._format_timestamp(segment['start'])
                    end_time = self._format_timestamp(segment['end'])
                    original_text = segment['text'].strip()
                    speaker = segment.get('speaker')
                    
                    # Translate each segment
                    try:
                        translated_segment = self.translate_to_romanian(original_text)
                        if speaker:
                            f.write(f"[{start_time} -> {end_time}] [{speaker}] {translated_segment}\n")
                        else:
                            f.write(f"[{start_time} -> {end_time}] {translated_segment}\n")
                        
                        if self.debug and i <= 3:  # Show first 3 for debug
                            logger.debug(f"Segment {i}: '{original_text}' -> '{translated_segment}'")
                    except Exception as e:
                        logger.warning(f"Failed to translate segment {i}: {e}")
                        if speaker:
                            f.write(f"[{start_time} -> {end_time}] [{speaker}] {original_text}\n")
                        else:
                            f.write(f"[{start_time} -> {end_time}] {original_text}\n")
                
                logger.info(f"✓ Translated {len(segments)} segments with timestamps")
                f.write("\n")
            elif segments:
                f.write("TIMESTAMPS (Translation unavailable):\n")
                f.write("-" * 40 + "\n")
                for segment in segments:
                    start_time = self._format_timestamp(segment['start'])
                    end_time = self._format_timestamp(segment['end'])
                    text = segment['text'].strip()
                    f.write(f"[{start_time} -> {end_time}] {text}\n")
                f.write("\n")
            
            f.write("="*80 + "\n")
            f.write("End of translation\n")
            f.write("="*80 + "\n")
    
    def _write_translated_subtitle_output(self, output_path, segments, format_type):
        """Write Romanian translation to subtitle file (SRT or VTT)."""
        logger.info(f"Generating translated {format_type.upper()} subtitle file...")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            if format_type == 'vtt':
                f.write("WEBVTT\n\n")
            
            for i, segment in enumerate(segments, 1):
                start_time = self._format_timestamp(segment['start'], format_type)
                end_time = self._format_timestamp(segment['end'], format_type)
                text = segment['text'].strip()
                speaker = segment.get('speaker')
                
                # Translate each segment
                if self.translator_available:
                    try:
                        text = self.translate_to_romanian(text)
                    except Exception as e:
                        logger.warning(f"Failed to translate segment {i}: {e}")
                        # Keep original if translation fails
                
                # Add speaker label if available
                if speaker:
                    text = f"[{speaker}] {text}"
                
                if format_type == 'srt':
                    f.write(f"{i}\n")
                    f.write(f"{start_time} --> {end_time}\n")
                    f.write(f"{text}\n\n")
                else:  # vtt
                    f.write(f"{start_time} --> {end_time}\n")
                    f.write(f"{text}\n\n")
        
        logger.info(f"✓ Translated subtitle file created with {len(segments)} segments")
    
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
    
    @staticmethod
    def _get_language_name(lang_code):
        """Get language name from ISO 639-1 code."""
        lang_names = {
            'en': 'English',
            'ro': 'Romanian',
            'es': 'Spanish',
            'fr': 'French',
            'de': 'German',
            'it': 'Italian',
            'pt': 'Portuguese',
            'ru': 'Russian',
            'ja': 'Japanese',
            'ko': 'Korean',
            'zh': 'Chinese',
            'ar': 'Arabic',
            'hi': 'Hindi',
            'nl': 'Dutch',
            'pl': 'Polish',
            'tr': 'Turkish',
            'sv': 'Swedish',
            'da': 'Danish',
            'no': 'Norwegian',
            'fi': 'Finnish',
        }
        return lang_names.get(lang_code, f"Unknown ({lang_code})")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Transcribe RO - Audio Transcription and Translation Tool for Romanian",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic transcription
  python transcribe_ro.py audio.mp3
  
  # Transcribe video file
  python transcribe_ro.py video.mp4
  
  # Transcribe without translation
  python transcribe_ro.py audio.mp3 --no-translate
  
  # Use a larger model for better accuracy
  python transcribe_ro.py audio.mp3 --model medium
  
  # Output as JSON
  python transcribe_ro.py audio.mp3 --format json
  
  # Generate subtitle file
  python transcribe_ro.py audio.mp3 --format srt
  
  # Force CPU usage (bypass GPU issues)
  python transcribe_ro.py audio.mp3 --force-cpu
  
  # Specify output file
  python transcribe_ro.py audio.mp3 --output result.txt
  
  # Batch process all files in a directory
  python transcribe_ro.py --directory /path/to/audio/files
  
  # Speaker diarization with two speakers
  python transcribe_ro.py audio.mp3 --speakers "John,Mary"
        """
    )
    
    # Required arguments
    parser.add_argument(
        'audio_file',
        type=str,
        nargs='?',
        default=None,
        help='Path to audio/video file (MP3, WAV, M4A, MP4, AVI, etc.)'
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
        default='small',
        help='Whisper model size (default: small). Larger models are more accurate but slower.'
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
        choices=['auto', 'cpu', 'mps', 'cuda'],
        default='auto',
        help='Device to run on (default: auto). Options: auto (detect best), cpu, mps (Apple Silicon), cuda (NVIDIA).'
    )
    
    parser.add_argument(
        '--force-cpu',
        action='store_true',
        help='Force CPU usage, bypassing GPU acceleration. Useful to avoid MPS/CUDA issues.'
    )
    
    parser.add_argument(
        '--translation-mode',
        type=str,
        choices=['auto', 'online', 'offline'],
        default='auto',
        help='Translation mode (default: auto). Options: auto (try online first, fallback to offline), online (requires internet), offline (uses local models)'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable detailed debug output for troubleshooting'
    )
    
    parser.add_argument(
        '-d', '--directory',
        type=str,
        default=None,
        help='Process all audio/video files in the specified directory (batch mode)'
    )
    
    parser.add_argument(
        '--speakers',
        type=str,
        default=None,
        help='Enable speaker diarization with two speaker names separated by comma (e.g., "John,Mary")'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='Transcribe RO v1.2.0'
    )
    
    args = parser.parse_args()
    
    # Setup logging based on debug flag
    setup_logging(debug=args.debug)
    
    # Re-enable warnings in debug mode
    if args.debug:
        warnings.filterwarnings('default')
    
    # Validate that either audio_file or directory is provided
    if not args.audio_file and not args.directory:
        logger.error("Error: Either audio_file or --directory must be specified")
        parser.print_help()
        sys.exit(1)
    
    if args.audio_file and args.directory:
        logger.error("Error: Cannot specify both audio_file and --directory")
        sys.exit(1)
    
    # Validate audio file if provided
    if args.audio_file and not os.path.exists(args.audio_file):
        logger.error(f"Audio file not found: {args.audio_file}")
        sys.exit(1)
    
    # Validate directory if provided
    if args.directory and not os.path.isdir(args.directory):
        logger.error(f"Directory not found: {args.directory}")
        sys.exit(1)
    
    # Check file extension (audio and video formats) - only for single file mode
    supported_audio_formats = ['.mp3', '.wav', '.m4a', '.flac', '.ogg', '.wma', '.aac', '.opus']
    supported_video_formats = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm', '.mpeg', '.mpg']
    supported_formats = supported_audio_formats + supported_video_formats
    
    if args.audio_file:
        file_ext = Path(args.audio_file).suffix.lower()
        if file_ext not in supported_formats:
            logger.warning(f"File format '{file_ext}' may not be supported.")
            logger.warning(f"Supported audio formats: {', '.join(supported_audio_formats)}")
            logger.warning(f"Supported video formats: {', '.join(supported_video_formats)}")
            response = input("Continue anyway? (y/n): ")
            if response.lower() != 'y':
                sys.exit(0)
        
        # Inform user if processing a video file
        if file_ext in supported_video_formats:
            logger.info(f"Video file detected ({file_ext}). Audio will be extracted automatically.")
    
    # Print banner
    print("\n" + "="*80)
    print("TRANSCRIBE RO - Audio Transcription & Translation Tool")
    print("="*80 + "\n")
    
    # Preload model to ensure it's downloaded
    logger.info(f"Checking/downloading Whisper model '{args.model}'...")
    if preload_model(args.model, debug=args.debug):
        logger.info(f"✓ Model '{args.model}' is ready")
    
    try:
        if args.debug:
            logger.debug("="*80)
            logger.debug("STARTING TRANSCRIPTION PROCESS")
            logger.debug("="*80)
            logger.debug(f"Command line arguments:")
            for arg, value in vars(args).items():
                logger.debug(f"  {arg}: {value}")
        
        # Initialize transcriber
        process_start = time.time() if args.debug else None
        
        # Handle --force-cpu flag
        device_to_use = 'cpu' if args.force_cpu else args.device
        if args.force_cpu:
            logger.info("--force-cpu flag detected: GPU acceleration disabled")
            if args.debug:
                logger.debug("User requested CPU-only mode via --force-cpu flag")
        
        transcriber = AudioTranscriber(
            model_name=args.model,
            device=device_to_use,
            debug=args.debug,
            translation_mode=args.translation_mode
        )
        
        # Process audio - either single file or batch directory
        if args.directory:
            # Batch directory processing
            results = process_directory(
                args.directory,
                transcriber,
                args,
                supported_formats
            )
            
            if not results:
                logger.error("No files were processed successfully")
                sys.exit(1)
            
            # For batch mode, we don't have a single result to display
            result = None
        else:
            # Single file processing
            result = transcriber.process_audio(
                audio_path=args.audio_file,
                output_path=args.output,
                translate=not args.no_translate,
                include_timestamps=not args.no_timestamps,
                output_format=args.format,
                speaker_names=args.speakers.split(',') if args.speakers else None
            )
        
        if args.debug and result:
            total_time = time.time() - process_start
            logger.debug("="*80)
            logger.debug("PROCESSING SUMMARY")
            logger.debug("="*80)
            logger.debug(f"Total processing time: {total_time:.2f} seconds")
            logger.debug(f"Detected language: {result['detected_language']}")
            logger.debug(f"Original transcription file: {result['output_file']}")
            if result.get('translated_output_file'):
                logger.debug(f"Translated file: {result['translated_output_file']}")
            logger.debug(f"Transcription length: {len(result['transcribed_text'])} chars")
            if result.get('translated_text'):
                logger.debug(f"Translation length: {len(result['translated_text'])} chars")
                logger.debug(f"Translation different from original: {result['translated_text'] != result['transcribed_text']}")
        
        print("\n" + "="*80)
        print("PROCESSING COMPLETED SUCCESSFULLY!")
        print("="*80)
        
        if result:  # Single file mode
            logger.info(f"Detected language: {result['detected_language']}")
            logger.info(f"Original transcription: {result['output_file']}")
            
            if result.get('translated_output_file'):
                logger.info(f"Romanian translation: {result['translated_output_file']}")
                logger.info("✓ Two files created: original transcription + Romanian translation")
        # Batch mode summary already printed by process_directory
        
    except KeyboardInterrupt:
        logger.warning("\nProcess interrupted by user.")
        if args.debug:
            logger.debug("KeyboardInterrupt received")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\nError: {e}")
        if args.debug:
            logger.debug("="*80)
            logger.debug("FULL EXCEPTION DETAILS")
            logger.debug("="*80)
            import traceback
            logger.debug(traceback.format_exc())
        else:
            logger.info("Run with --debug flag for detailed error information")
        sys.exit(1)


if __name__ == "__main__":
    main()
