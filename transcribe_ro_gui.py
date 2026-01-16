#!/usr/bin/env python3
"""
Transcribe RO - GUI Application
A graphical user interface for audio transcription and translation to Romanian.

Features:
- File selection for audio files
- Language selection (Romanian as default)
- Two-panel display: Original transcript and Romanian translation
- Progress tracking and status updates
- Copy and Save functionality
- Speaker recognition with up to 4 speakers
- Cross-platform compatibility (macOS, Windows, Linux)

Author: transcribe_ro
License: MIT
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path
import logging
from PIL import Image, ImageTk

# Import preferences system
try:
    from preferences import SettingsManager, show_preferences_dialog
    PREFERENCES_AVAILABLE = True
except ImportError:
    PREFERENCES_AVAILABLE = False
    print("Warning: Preferences module not found. Settings dialog will be unavailable.")

# Set MPS-specific environment variables for stability
# These help prevent NaN issues on Apple Silicon GPUs
os.environ['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'
os.environ['PYTORCH_MPS_HIGH_WATERMARK_RATIO'] = '0.0'

# Import the AudioTranscriber class from transcribe_ro
try:
    from transcribe_ro import (
        AudioTranscriber, 
        setup_logging, 
        perform_speaker_diarization, 
        get_speaker_for_timestamp,
        check_diarization_requirements,
        DIARIZATION_AVAILABLE,
        # Video support
        is_video_file,
        is_audio_file,
        extract_audio_from_video,
        VIDEO_EXTENSIONS,
        AUDIO_EXTENSIONS
    )
except ImportError:
    print("Error: Could not import transcribe_ro module.")
    print("Make sure transcribe_ro.py is in the same directory.")
    sys.exit(1)


class TranscribeROGUI:
    """Main GUI application class for Transcribe RO."""
    
    # Maximum number of speakers supported
    MAX_SPEAKERS = 4
    
    def __init__(self, root):
        """Initialize the GUI application."""
        self.root = root
        self.root.title("Transcribe RO - Transcriere Audio și Traducere (Audio Transcription & Translation)")
        self.root.geometry("1200x800")
        
        # Setup logging FIRST - before anything else that might need logging
        setup_logging(debug=False)
        self.logger = logging.getLogger(__name__)
        
        # Track if HF token was loaded from settings (for UI feedback)
        self.hf_token_loaded_from_settings = False
        
        # Initialize settings manager and load saved settings
        self.settings_manager = None
        if PREFERENCES_AVAILABLE:
            self.settings_manager = SettingsManager()
            self._apply_saved_settings()
        
        # Load branding images
        self.gen_logo_image = None
        self.flag_icon_image = None
        self._load_branding_images()
        
        # Configure window icon (Romanian flag)
        self._set_window_icon()
        
        # Variables
        self.selected_file = tk.StringVar()
        self.source_language = tk.StringVar(value="ro")  # Romanian as default
        self.translation_status = tk.StringVar(value="Neînceput (Not started)")
        
        # Speaker name variables (support up to 4 speakers)
        self.speaker_names = []
        for i in range(self.MAX_SPEAKERS):
            self.speaker_names.append(tk.StringVar(value=""))
        
        # For backward compatibility
        self.speaker1_name = self.speaker_names[0]
        self.speaker2_name = self.speaker_names[1]
        
        # Track number of visible speaker fields (start with 2)
        self.visible_speakers = 2
        
        # Speaker name assignments (maps "Speaker 1" -> assigned name)
        self.speaker_assignments = {}
        
        # Enable diarization checkbox variable
        self.enable_diarization = tk.BooleanVar(value=False)
        
        self.debug_mode = tk.BooleanVar(value=False)  # Debug mode toggle
        self.processing = False
        self.transcriber = None
        self.current_result = None  # Store the transcription result with segments
        self.diarization_segments = None  # Store segments with speaker info for later use
        self.speaker_timeline = None  # Store diarization timeline
        
        # Language options
        self.languages = {
            "ro": "Română (Romanian)",
            "en": "English",
            "es": "Spanish (Español)",
            "fr": "French (Français)",
            "de": "German (Deutsch)",
            "it": "Italian (Italiano)",
            "pt": "Portuguese (Português)",
            "ru": "Russian (Русский)",
            "zh": "Chinese (中文)",
            "ja": "Japanese (日本語)",
            "ar": "Arabic (العربية)",
            "hi": "Hindi (हिन्दी)",
            "nl": "Dutch (Nederlands)",
            "pl": "Polish (Polski)",
            "tr": "Turkish (Türkçe)"
        }
        
        # Supported audio and video formats
        self.audio_formats = [
            ("Audio/Video Files", "*.mp3 *.wav *.m4a *.flac *.ogg *.wma *.aac *.opus *.mp4 *.avi *.mkv *.mov *.wmv *.webm *.m4v"),
            ("Audio Files", "*.mp3 *.wav *.m4a *.flac *.ogg *.wma *.aac *.opus"),
            ("Video Files", "*.mp4 *.avi *.mkv *.mov *.wmv *.webm *.m4v *.mpeg *.mpg"),
            ("MP3 Files", "*.mp3"),
            ("WAV Files", "*.wav"),
            ("MP4 Files", "*.mp4"),
            ("All Files", "*.*")
        ]
        
        # Create GUI elements
        self.create_widgets()
        
        # Center window on screen
        self.center_window()
    
    def center_window(self):
        """Center the window on the screen."""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def _apply_saved_settings(self):
        """Apply saved settings on application startup."""
        if not self.settings_manager:
            self.logger.debug("Settings manager not available")
            return
        
        self.logger.info("Loading settings from config file...")
        
        # Check if there's a saved HF token
        saved_token = self.settings_manager.get_hf_token()
        
        if saved_token:
            self.logger.info(f"Found saved HF token (length: {len(saved_token)}, prefix: {saved_token[:7]}...)")
            
            # Always apply the HF token to environment variable
            # The auto_load setting is for future use with other settings
            os.environ['HF_TOKEN'] = saved_token
            self.hf_token_loaded_from_settings = True
            self.logger.info("HF_TOKEN successfully set in environment from saved preferences")
            
            # Verify it was set
            if os.environ.get('HF_TOKEN'):
                self.logger.info("Verification: HF_TOKEN is now available in os.environ")
            else:
                self.logger.error("Verification FAILED: HF_TOKEN not found in os.environ after setting")
        else:
            self.logger.info("No HF_TOKEN found in saved settings - speaker diarization will require manual token entry")
            self.hf_token_loaded_from_settings = False
    
    def _get_assets_path(self):
        """Get the path to the assets directory."""
        # Try relative to script location first
        script_dir = Path(__file__).parent.resolve()
        assets_dir = script_dir / "assets"
        if assets_dir.exists():
            return assets_dir
        # Fallback to current working directory
        cwd_assets = Path.cwd() / "assets"
        if cwd_assets.exists():
            return cwd_assets
        return None
    
    def _load_branding_images(self):
        """Load branding images (GEN logo and Romanian flag)."""
        assets_path = self._get_assets_path()
        if not assets_path:
            self.logger.warning("Assets directory not found, branding images will not be displayed")
            return
        
        # Load GEN logo for header
        gen_logo_path = assets_path / "gen_logo.png"
        if gen_logo_path.exists():
            try:
                img = Image.open(gen_logo_path)
                # Resize to 50px height, maintaining aspect ratio
                target_height = 50
                aspect_ratio = img.width / img.height
                target_width = int(target_height * aspect_ratio)
                img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
                self.gen_logo_image = ImageTk.PhotoImage(img)
                self.logger.info(f"GEN logo loaded successfully ({target_width}x{target_height})")
            except Exception as e:
                self.logger.warning(f"Could not load GEN logo: {e}")
        
        # Load Romanian flag for window icon
        flag_path = assets_path / "romanian_flag.png"
        if flag_path.exists():
            try:
                img = Image.open(flag_path)
                # Resize for window icon (typically 32x32 or 64x64)
                img_icon = img.resize((64, 64), Image.Resampling.LANCZOS)
                self.flag_icon_image = ImageTk.PhotoImage(img_icon)
                self.logger.info("Romanian flag icon loaded successfully")
            except Exception as e:
                self.logger.warning(f"Could not load Romanian flag: {e}")
    
    def _set_window_icon(self):
        """Set the window icon to the Romanian flag."""
        if self.flag_icon_image:
            try:
                self.root.iconphoto(True, self.flag_icon_image)
                self.logger.info("Window icon set to Romanian flag")
            except Exception as e:
                self.logger.warning(f"Could not set window icon: {e}")
    
    def open_preferences(self):
        """Open the preferences dialog."""
        if not PREFERENCES_AVAILABLE or not self.settings_manager:
            messagebox.showerror("Error", "Preferences module not available.")
            return
        
        show_preferences_dialog(
            self.root,
            self.settings_manager,
            on_settings_saved=self._on_settings_saved
        )
    
    def _on_settings_saved(self):
        """Callback when settings are saved - update UI accordingly."""
        # Check if HF_TOKEN is now available in environment
        if os.environ.get('HF_TOKEN'):
            self.hf_token_loaded_from_settings = True
            self.logger.info("Settings saved - HF_TOKEN is available in environment")
        # Update speaker recognition status
        self._update_speaker_status()
    
    def _update_speaker_status(self):
        """Update the speaker recognition status indicator."""
        if not hasattr(self, 'speaker_status_label'):
            return
        
        # Re-check diarization requirements (which will now include the new HF_TOKEN)
        is_available, error_msg = check_diarization_requirements()
        
        if is_available:
            # Check if token was loaded from settings vs manually set
            if getattr(self, 'hf_token_loaded_from_settings', False):
                status_text = "✓ Token încărcat din preferințe - recunoașterea vorbitorilor disponibilă (Token loaded from preferences - speaker recognition available)"
            else:
                status_text = "✓ Recunoașterea vorbitorilor este disponibilă (Speaker recognition is available)"
            status_color = "green"
        elif not DIARIZATION_AVAILABLE:
            status_text = "⚠️ pyannote.audio nu este instalat (pyannote.audio not installed)"
            status_color = "orange"
        else:
            # HF_TOKEN missing
            status_text = "⚠️ HF_TOKEN lipsește - folosiți Preferințe (HF_TOKEN missing - use Preferences)"
            status_color = "orange"
        
        self.speaker_status_label.config(text=status_text, foreground=status_color)
    
    def toggle_debug_mode(self):
        """Toggle debug mode and reinitialize logging."""
        debug_enabled = self.debug_mode.get()
        
        # Reinitialize logging with new debug setting
        setup_logging(debug=debug_enabled)
        self.logger = logging.getLogger(__name__)
        
        if debug_enabled:
            self.logger.info("Debug mode ENABLED - verbose logging active")
            self.update_status("🐛 Mod debug activat - jurnalizare verbosă (Debug mode enabled - verbose logging)", "blue")
        else:
            self.logger.info("Debug mode DISABLED - normal logging")
            self.update_status("Debug mode dezactivat (Debug mode disabled)", "gray")
    
    def create_widgets(self):
        """Create all GUI widgets."""
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights for resizing
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Header
        self.create_header(main_frame)
        
        # File selection section
        self.create_file_selection(main_frame)
        
        # Source Language (LEFT) and Speaker Recognition (RIGHT) side by side
        self.create_language_and_speaker_section(main_frame)
        
        # Control buttons
        self.create_control_buttons(main_frame)
        
        # Progress bar
        self.create_progress_bar(main_frame)
        
        # Status message
        self.create_status_message(main_frame)
        
        # Results section (two side-by-side panels) - expanded
        self.create_results_section(main_frame)
    
    def create_header(self, parent):
        """Create the header section."""
        header_frame = ttk.Frame(parent)
        header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        header_frame.columnconfigure(1, weight=1)  # Title column expands
        
        # Left side: Logo + Title and subtitle
        title_frame = ttk.Frame(header_frame)
        title_frame.grid(row=0, column=0, columnspan=2, sticky=tk.W)
        
        # Column counter for dynamic positioning
        col = 0
        
        # GEN Logo (if available)
        if self.gen_logo_image:
            logo_label = ttk.Label(title_frame, image=self.gen_logo_image)
            logo_label.grid(row=0, column=col, rowspan=2, sticky=tk.W, padx=(0, 10))
            col += 1
        
        title_label = ttk.Label(
            title_frame,
            text="🎙️ Transcribe RO",
            font=("Helvetica", 20, "bold")
        )
        title_label.grid(row=0, column=col, sticky=tk.W)
        
        subtitle_label = ttk.Label(
            title_frame,
            text="Transcriere Audio și Traducere în Română (Audio Transcription & Translation to Romanian)",
            font=("Helvetica", 10)
        )
        subtitle_label.grid(row=1, column=col, sticky=tk.W)
        
        # Right side: Debug checkbox and Settings button
        right_controls = ttk.Frame(header_frame)
        right_controls.grid(row=0, column=1, sticky=tk.E)
        
        # Debug mode checkbox
        debug_check = ttk.Checkbutton(
            right_controls,
            text="🐛 Debug Mode",
            variable=self.debug_mode,
            command=self.toggle_debug_mode
        )
        debug_check.grid(row=0, column=0, padx=(0, 10))
        
        if PREFERENCES_AVAILABLE:
            settings_btn = ttk.Button(
                right_controls,
                text="⚙️ Preferințe (Settings)",
                command=self.open_preferences,
                width=22
            )
            settings_btn.grid(row=0, column=1, sticky=tk.E)
    
    def create_file_selection(self, parent):
        """Create the file selection section."""
        file_frame = ttk.LabelFrame(parent, text="Selecție Fișier Audio (Audio File Selection)", padding="10")
        file_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        file_frame.columnconfigure(1, weight=1)
        
        # Browse button
        browse_btn = ttk.Button(
            file_frame,
            text="Răsfoiește (Browse)",
            command=self.browse_file,
            width=20
        )
        browse_btn.grid(row=0, column=0, padx=(0, 10))
        
        # File path display
        file_entry = ttk.Entry(
            file_frame,
            textvariable=self.selected_file,
            state="readonly"
        )
        file_entry.grid(row=0, column=1, sticky=(tk.W, tk.E))
        
        # Clear button
        clear_btn = ttk.Button(
            file_frame,
            text="Șterge (Clear)",
            command=self.clear_file,
            width=15
        )
        clear_btn.grid(row=0, column=2, padx=(10, 0))
    
    def create_language_and_speaker_section(self, parent):
        """Create Source Language (LEFT) and Speaker Recognition (RIGHT) side by side."""
        # Container for both sections
        container = ttk.Frame(parent)
        container.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        container.columnconfigure(0, weight=1)
        container.columnconfigure(1, weight=1)
        
        # Left side: Language Selection
        lang_frame = ttk.LabelFrame(container, text="Limbă Sursă (Source Language)", padding="10")
        lang_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        lang_frame.columnconfigure(0, weight=1)
        
        # Add language radio buttons in a grid (no scrolling needed)
        lang_buttons_frame = ttk.Frame(lang_frame)
        lang_buttons_frame.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        row, col = 0, 0
        max_cols = 3
        
        for lang_code, lang_name in self.languages.items():
            rb = ttk.Radiobutton(
                lang_buttons_frame,
                text=lang_name,
                variable=self.source_language,
                value=lang_code
            )
            rb.grid(row=row, column=col, sticky=tk.W, padx=5, pady=2)
            
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
        
        # Info label
        info_label = ttk.Label(
            lang_frame,
            text="ℹ️ Româna este selectată implicit. Dacă audio-ul este deja în română, se va afișa doar transcrierea.",
            font=("Helvetica", 9),
            foreground="blue",
            wraplength=350
        )
        info_label.grid(row=1, column=0, sticky=tk.W, pady=(10, 0))
        
        # Right side: Speaker Recognition
        speaker_frame = ttk.LabelFrame(container, text="🎤 Recunoaștere Vorbitori (Speaker Recognition)", padding="10")
        speaker_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0))
        speaker_frame.columnconfigure(1, weight=1)
        self.speaker_frame = speaker_frame  # Store reference for dynamic updates
        
        # Enable diarization checkbox (row 0)
        self.enable_diarization_checkbox = ttk.Checkbutton(
            speaker_frame,
            text="✓ Activează Diarizarea (Enable Speaker Diarization)",
            variable=self.enable_diarization,
            command=self._on_diarization_toggle
        )
        self.enable_diarization_checkbox.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))
        
        # Create speaker entry widgets (store references for dynamic show/hide)
        # Start from row 1 (after the checkbox)
        self.speaker_labels = []
        self.speaker_entries = []
        
        for i in range(self.MAX_SPEAKERS):
            label = ttk.Label(speaker_frame, text=f"Nume Vorbitor {i+1} (Speaker {i+1} Name):")
            entry = ttk.Entry(speaker_frame, textvariable=self.speaker_names[i], width=25)
            
            self.speaker_labels.append(label)
            self.speaker_entries.append(entry)
            
            # Initially show only the first 2 speakers (offset by 1 for checkbox)
            if i < self.visible_speakers:
                label.grid(row=i+1, column=0, sticky=tk.W, padx=(0, 10))
                entry.grid(row=i+1, column=1, sticky=(tk.W, tk.E), pady=2)
        
        # Row index for elements below speakers (offset by 1 for checkbox)
        self.speaker_buttons_row = self.MAX_SPEAKERS + 1
        
        # Add Speaker button (only show if we can add more)
        self.add_speaker_btn = ttk.Button(
            speaker_frame,
            text="+ Adaugă Vorbitor (Add Speaker)",
            command=self.add_speaker,
            width=28
        )
        self.add_speaker_btn.grid(row=self.speaker_buttons_row, column=0, columnspan=2, sticky=tk.W, pady=(5, 5))
        
        # Check diarization availability and show appropriate status
        is_available, error_msg = check_diarization_requirements()
        
        if is_available:
            # Check if token was loaded from settings vs manually set
            if getattr(self, 'hf_token_loaded_from_settings', False):
                status_text = "✓ Token încărcat din preferințe (Token loaded from preferences)"
            else:
                status_text = "✓ Recunoașterea vorbitorilor disponibilă (Speaker recognition available)"
            status_color = "green"
        elif not DIARIZATION_AVAILABLE:
            status_text = "⚠️ pyannote.audio nu este instalat (not installed)"
            status_color = "orange"
        else:
            # HF_TOKEN missing - reference preferences
            status_text = "⚠️ HF_TOKEN lipsește - folosiți ⚙️ Preferințe"
            status_color = "orange"
        
        # Status label
        self.speaker_status_label = ttk.Label(
            speaker_frame,
            text=status_text,
            font=("Helvetica", 9),
            foreground=status_color
        )
        self.speaker_status_label.grid(row=self.speaker_buttons_row + 1, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))
        
        # Add clickable link to preferences for HF token setup
        if PREFERENCES_AVAILABLE:
            hf_link_btn = ttk.Label(
                speaker_frame,
                text="Configurați token în Preferințe (Configure in Preferences) →",
                font=("Helvetica", 8, "underline"),
                foreground="blue",
                cursor="hand2"
            )
            hf_link_btn.grid(row=self.speaker_buttons_row + 2, column=0, columnspan=2, sticky=tk.W, pady=(2, 0))
            hf_link_btn.bind("<Button-1>", lambda e: self.open_preferences())
        
        # Assign Speakers button - at the lower left corner of the speaker panel
        self.assign_speakers_btn = ttk.Button(
            speaker_frame,
            text="✓ Atribuie Vorbitori (Assign Speakers)",
            command=self.assign_speakers,
            width=32
        )
        self.assign_speakers_btn.grid(row=self.speaker_buttons_row + 3, column=0, columnspan=2, sticky=tk.W, pady=(10, 0))
    
    def _on_diarization_toggle(self):
        """Handle diarization checkbox toggle."""
        enabled = self.enable_diarization.get()
        if enabled:
            self.logger.info("Speaker diarization enabled")
            self.update_status("✓ Diarizarea vorbitorilor activată (Speaker diarization enabled)", "green")
        else:
            self.logger.info("Speaker diarization disabled")
            self.update_status("Diarizarea vorbitorilor dezactivată (Speaker diarization disabled)", "gray")
    
    def add_speaker(self):
        """Add a new speaker input field (up to MAX_SPEAKERS)."""
        if self.visible_speakers >= self.MAX_SPEAKERS:
            messagebox.showinfo(
                "Limită atinsă (Limit Reached)",
                f"Numărul maxim de vorbitori ({self.MAX_SPEAKERS}) a fost atins.\n"
                f"(Maximum number of speakers ({self.MAX_SPEAKERS}) has been reached.)"
            )
            return
        
        # Show the next speaker field (offset by 1 for checkbox row)
        idx = self.visible_speakers
        self.speaker_labels[idx].grid(row=idx+1, column=0, sticky=tk.W, padx=(0, 10))
        self.speaker_entries[idx].grid(row=idx+1, column=1, sticky=(tk.W, tk.E), pady=2)
        
        self.visible_speakers += 1
        self.logger.info(f"Added speaker {self.visible_speakers}")
        
        # Hide the add button if we've reached the maximum
        if self.visible_speakers >= self.MAX_SPEAKERS:
            self.add_speaker_btn.config(state="disabled")
    
    def assign_speakers(self):
        """Assign speaker names to the transcription display."""
        # Check if we have diarization data
        if not self.diarization_segments:
            messagebox.showwarning(
                "Fără date de diarizare (No Diarization Data)",
                "Nu există date de recunoaștere a vorbitorilor.\n"
                "Vă rugăm să efectuați mai întâi o transcriere cu diarizarea activată.\n\n"
                "(No speaker recognition data available.\n"
                "Please perform a transcription with diarization enabled first.)"
            )
            return
        
        # Build speaker assignments dictionary
        self.speaker_assignments = {}
        assigned_count = 0
        
        for i in range(self.visible_speakers):
            name = self.speaker_names[i].get().strip()
            if name:
                # Map "Speaker 1" (or similar default labels) to the assigned name
                self.speaker_assignments[f"Speaker {i+1}"] = name
                self.speaker_assignments[f"SPEAKER_{i:02d}"] = name  # pyannote format
                assigned_count += 1
        
        self.logger.info(f"Speaker assignments: {self.speaker_assignments}")
        
        # Re-format the displays with speaker labels included
        # Use stored segments with speaker info
        formatted_original = self._format_text_with_timestamps(
            self.diarization_segments['original'], 
            include_speakers=True
        )
        self.original_text.delete(1.0, tk.END)
        self.original_text.insert(1.0, formatted_original)
        
        # If we have translated segments, update those too
        if self.diarization_segments.get('translated'):
            formatted_translation = self._format_text_with_timestamps(
                self.diarization_segments['translated'],
                include_speakers=True
            )
            self.translation_text.delete(1.0, tk.END)
            self.translation_text.insert(1.0, formatted_translation)
        
        # Show confirmation
        if assigned_count > 0:
            assigned_names = ", ".join([f"Speaker {i+1} → {self.speaker_names[i].get().strip()}" 
                                         for i in range(self.visible_speakers) 
                                         if self.speaker_names[i].get().strip()])
            
            messagebox.showinfo(
                "Vorbitori Atribuiți (Speakers Assigned)",
                f"Numele vorbitorilor au fost atribuite:\n{assigned_names}\n\n"
                f"(Speaker names have been assigned:\n{assigned_names})"
            )
            self.update_status(f"✓ {assigned_count} nume de vorbitori atribuite (speaker names assigned)", "green")
        else:
            messagebox.showinfo(
                "Niciun Nume de Vorbitor (No Speaker Names)",
                "Nu ați introdus niciun nume de vorbitor.\n"
                "Transcrierea rămâne fără etichete de vorbitor.\n\n"
                "(You have not entered any speaker names.\n"
                "The transcription remains without speaker labels.)"
            )
            self.update_status("ℹ️ Niciun nume de vorbitor introdus (No speaker names entered)", "blue")
    
    def get_speaker_names_for_diarization(self):
        """Get the list of speaker names for diarization (non-empty ones)."""
        names = []
        for i in range(self.visible_speakers):
            name = self.speaker_names[i].get().strip()
            if name:
                names.append(name)
            else:
                # Use default label if no name provided
                names.append(f"Speaker {i+1}")
        return names
    
    def create_control_buttons(self, parent):
        """Create control buttons."""
        button_frame = ttk.Frame(parent)
        button_frame.grid(row=3, column=0, columnspan=2, pady=(0, 10))
        
        # Process button
        self.process_btn = ttk.Button(
            button_frame,
            text="🎬 Începe Transcrierea (Start Transcription)",
            command=self.start_processing,
            width=40
        )
        self.process_btn.grid(row=0, column=0, padx=5)
        
        # Stop button (initially disabled)
        self.stop_btn = ttk.Button(
            button_frame,
            text="⏹️ Oprește (Stop)",
            command=self.stop_processing,
            state="disabled",
            width=20
        )
        self.stop_btn.grid(row=0, column=1, padx=5)
    
    def create_progress_bar(self, parent):
        """Create progress bar."""
        progress_frame = ttk.Frame(parent)
        progress_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        progress_frame.columnconfigure(0, weight=1)
        
        self.progress = ttk.Progressbar(
            progress_frame,
            mode='indeterminate',
            length=300
        )
        self.progress.grid(row=0, column=0, sticky=(tk.W, tk.E))
    
    def create_status_message(self, parent):
        """Create status message label."""
        status_frame = ttk.Frame(parent)
        status_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.status_label = ttk.Label(
            status_frame,
            text="Gata. Selectați un fișier audio pentru a începe. (Ready. Please select an audio file to begin.)",
            font=("Helvetica", 10),
            foreground="gray"
        )
        self.status_label.grid(row=0, column=0, sticky=tk.W)
    
    def create_results_section(self, parent):
        """Create the results section with two side-by-side panels."""
        results_frame = ttk.LabelFrame(parent, text="Rezultate (Results)", padding="10")
        results_frame.grid(row=6, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 0))
        
        # Configure grid weights for resizing - give more weight to results section
        parent.rowconfigure(6, weight=3)  # Give results section 3x weight
        results_frame.columnconfigure(0, weight=1)
        results_frame.columnconfigure(1, weight=1)
        results_frame.rowconfigure(1, weight=1)
        
        # Left panel - Original Transcript
        left_frame = ttk.Frame(results_frame)
        left_frame.grid(row=0, column=0, rowspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(1, weight=1)
        
        ttk.Label(
            left_frame,
            text="Transcriere Originală (Original Transcript)",
            font=("Helvetica", 11, "bold")
        ).grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        self.original_text = scrolledtext.ScrolledText(
            left_frame,
            wrap=tk.WORD,
            width=40,
            height=15,
            font=("Helvetica", 10)
        )
        self.original_text.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Left panel buttons
        left_buttons = ttk.Frame(left_frame)
        left_buttons.grid(row=2, column=0, sticky=tk.W, pady=(5, 0))
        
        ttk.Button(
            left_buttons,
            text="📋 Copiază (Copy)",
            command=lambda: self.copy_text(self.original_text),
            width=18
        ).grid(row=0, column=0, padx=(0, 5))
        
        ttk.Button(
            left_buttons,
            text="💾 Salvează (Save)",
            command=lambda: self.save_text(self.original_text, "original"),
            width=18
        ).grid(row=0, column=1)
        
        # Right panel - Romanian Translation
        right_frame = ttk.Frame(results_frame)
        right_frame.grid(row=0, column=1, rowspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0))
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(1, weight=1)
        
        ttk.Label(
            right_frame,
            text="Traducere în Română (Romanian Translation)",
            font=("Helvetica", 11, "bold")
        ).grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        self.translation_text = scrolledtext.ScrolledText(
            right_frame,
            wrap=tk.WORD,
            width=40,
            height=15,
            font=("Helvetica", 10)
        )
        self.translation_text.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Right panel buttons
        right_buttons = ttk.Frame(right_frame)
        right_buttons.grid(row=2, column=0, sticky=tk.W, pady=(5, 0))
        
        ttk.Button(
            right_buttons,
            text="📋 Copiază (Copy)",
            command=lambda: self.copy_text(self.translation_text),
            width=18
        ).grid(row=0, column=0, padx=(0, 5))
        
        ttk.Button(
            right_buttons,
            text="💾 Salvează (Save)",
            command=lambda: self.save_text(self.translation_text, "translation"),
            width=18
        ).grid(row=0, column=1)
    
    def browse_file(self):
        """Open file browser to select audio file."""
        filename = filedialog.askopenfilename(
            title="Selectați Fișier Audio (Select Audio File)",
            filetypes=self.audio_formats
        )
        
        if filename:
            self.selected_file.set(filename)
            self.update_status(f"Selectat (Selected): {Path(filename).name}", "blue")
    
    def clear_file(self):
        """Clear selected file."""
        self.selected_file.set("")
        # Clear stored diarization data
        self.diarization_segments = None
        self.speaker_timeline = None
        self.speaker_assignments = {}
        self.update_status("Fișier șters. Gata să selectați un nou fișier. (File cleared. Ready to select new file.)", "gray")
    
    def update_status(self, message, color="black"):
        """Update status message."""
        self.status_label.config(text=message, foreground=color)
        self.root.update_idletasks()
    
    def start_processing(self):
        """Start the transcription process."""
        # Validate file selection
        if not self.selected_file.get():
            messagebox.showerror("Eroare (Error)", "Vă rugăm să selectați mai întâi un fișier audio. (Please select an audio file first.)")
            return
        
        if not os.path.exists(self.selected_file.get()):
            messagebox.showerror("Eroare (Error)", "Fișierul selectat nu există. (Selected file does not exist.)")
            return
        
        # Clear previous results and diarization data
        self.original_text.delete(1.0, tk.END)
        self.translation_text.delete(1.0, tk.END)
        self.diarization_segments = None
        self.speaker_timeline = None
        self.speaker_assignments = {}
        
        # Update UI state
        self.processing = True
        self.process_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.progress.start(10)
        
        self.update_status("Se încarcă modelul și se pregătește transcrierea... (Loading model and preparing transcription...)", "orange")
        
        # Start processing in a separate thread to avoid UI freeze
        processing_thread = threading.Thread(target=self.process_audio, daemon=True)
        processing_thread.start()
    
    def stop_processing(self):
        """Stop the transcription process."""
        if messagebox.askyesno("Confirmare (Confirm)", "Sigur doriți să opriți transcrierea? (Are you sure you want to stop the transcription?)"):
            self.processing = False
            self.update_status("Procesare oprită de utilizator. (Processing stopped by user.)", "red")
            self.reset_ui_state()
    
    def process_audio(self):
        """Process the audio file (runs in separate thread)."""
        try:
            # Initialize transcriber
            self.root.after(0, lambda: self.update_status("Se încarcă modelul Whisper... (Loading Whisper model...)", "orange"))
            
            # Load settings from preferences
            model_size = "base"
            device_type = "auto"
            force_cpu = False
            translation_mode = "auto"
            
            if self.settings_manager:
                model_size = self.settings_manager.get("transcription", "default_model_size", "base")
                device_type = self.settings_manager.get("transcription", "default_device", "auto")
                force_cpu = self.settings_manager.get("transcription", "force_cpu", False)
                translation_mode = self.settings_manager.get("transcription", "default_translation_mode", "auto")
                self.logger.info(f"Loaded settings from preferences: model={model_size}, device={device_type}, force_cpu={force_cpu}, translation={translation_mode}")
            
            # Handle force CPU option
            device_to_use = 'cpu' if force_cpu else device_type
            if force_cpu:
                self.logger.info("Force CPU option enabled: GPU acceleration disabled")
            
            # Get current debug mode from checkbox
            debug_enabled = self.debug_mode.get()
            
            self.transcriber = AudioTranscriber(
                model_name=model_size,
                device=device_to_use,
                verbose=True,
                debug=debug_enabled,
                translation_mode=translation_mode
            )
            
            if not self.processing:
                return
            
            # Transcribe audio
            self.root.after(0, lambda: self.update_status("Se transcrie audio... Poate dura câteva minute. (Transcribing audio... This may take a few minutes.)", "orange"))
            
            result = self.transcriber.transcribe_audio(self.selected_file.get())
            
            if not self.processing:
                return
            
            detected_language = result.get('language', 'unknown')
            transcribed_text = result.get('text', '').strip()
            segments = result.get('segments', [])
            
            # Store the result for later use
            self.current_result = result
            
            # Perform speaker diarization if enabled via checkbox
            speaker_timeline = None
            diarization_status = None
            
            # Get all non-empty speaker names (optional - for custom labels)
            speaker_names_list = [self.speaker_names[i].get().strip() for i in range(self.visible_speakers) 
                                  if self.speaker_names[i].get().strip()]
            
            # Check if diarization is enabled via checkbox
            diarization_enabled = self.enable_diarization.get()
            
            if diarization_enabled:
                self.logger.info(f"Diarization enabled. Custom speaker names: {speaker_names_list if speaker_names_list else 'None (will use default labels)'}")
                
                # Pre-check diarization requirements before attempting
                is_available, prereq_error = check_diarization_requirements()
                
                if not is_available:
                    # Show warning to user about missing requirements
                    self.logger.warning(f"Speaker diarization unavailable: {prereq_error}")
                    diarization_status = prereq_error
                    
                    # Update GUI with clear error message
                    error_display = f"⚠️ Speaker recognition unavailable: {prereq_error}"
                    self.root.after(0, lambda msg=error_display: self.update_status(msg, "orange"))
                    
                    # Show message box with instructions
                    if "HF_TOKEN" in prereq_error:
                        self.root.after(0, lambda: messagebox.showwarning(
                            "Speaker Recognition - Token Required",
                            "Speaker recognition requires a HuggingFace token.\n\n"
                            "To enable speaker recognition:\n"
                            "1. Create a free account at huggingface.co\n"
                            "2. Get your token at: https://huggingface.co/settings/tokens\n"
                            "3. Go to ⚙️ Preferences and enter your token\n"
                            "4. Restart the application\n\n"
                            "Transcription will continue without speaker labels."
                        ))
                    elif "pyannote" in prereq_error:
                        self.root.after(0, lambda: messagebox.showwarning(
                            "Speaker Recognition - Not Installed",
                            "Speaker recognition requires pyannote.audio.\n\n"
                            "Install with: pip install pyannote.audio\n\n"
                            "Transcription will continue without speaker labels."
                        ))
                else:
                    # Requirements met, proceed with diarization
                    self.root.after(0, lambda: self.update_status(
                        "🎤 Se efectuează diarizarea vorbitorilor... (Performing speaker diarization...)", 
                        "orange"
                    ))
                    self.logger.info("Starting speaker diarization...")
                    
                    # Call diarization - pass custom names if provided, otherwise use defaults
                    # The diarization function will use "Speaker 1", "Speaker 2" etc. if no names provided
                    speaker_timeline, diarization_status = perform_speaker_diarization(
                        self.selected_file.get(),
                        speaker_names=speaker_names_list if speaker_names_list else None,
                        debug=debug_enabled
                    )
                    
                    # Add speaker labels to segments if diarization succeeded
                    if speaker_timeline:
                        self.logger.info(f"✓ {diarization_status}")
                        self.root.after(0, lambda msg=f"✓ {diarization_status}": self.update_status(msg, "green"))
                        
                        # Store the speaker timeline for later use
                        self.speaker_timeline = speaker_timeline
                        
                        for segment in segments:
                            segment_mid = (segment['start'] + segment['end']) / 2
                            speaker = get_speaker_for_timestamp(speaker_timeline, segment_mid)
                            segment['speaker'] = speaker if speaker else "Unknown"
                        
                        self.logger.info(f"Speaker labels assigned to {len(segments)} segments (stored for later display)")
                    else:
                        # Diarization failed after passing pre-checks
                        self.logger.warning(f"Speaker diarization failed: {diarization_status}")
                        self.root.after(0, lambda msg=f"⚠️ {diarization_status}": self.update_status(msg, "orange"))
                        self.root.after(0, lambda: messagebox.showwarning(
                            "Speaker Recognition Failed",
                            f"Speaker recognition encountered an error:\n\n{diarization_status}\n\n"
                            "Transcription will continue without speaker labels."
                        ))
            
            # Format original transcript with timestamps (NO speaker labels initially)
            # Speaker labels will only be shown when user clicks "Assign Speakers"
            formatted_transcript = self._format_text_with_timestamps(segments, speaker_timeline, include_speakers=False)
            
            # Store segments for later speaker assignment (if diarization was performed)
            if speaker_timeline:
                self.diarization_segments = {'original': segments, 'translated': None}
            else:
                self.diarization_segments = None
            
            # Display original transcript with timestamps
            self.root.after(0, lambda: self.original_text.insert(1.0, formatted_transcript))
            
            # Check if translation is needed
            if detected_language == 'ro':
                # Audio is already in Romanian - show the same formatted transcript
                self.root.after(0, lambda: self.translation_text.insert(
                    1.0,
                    "✓ Audio-ul sursă este deja în română.\n\n"
                    "Nu este necesară traducerea. Transcrierea cu marcaje de timp este afișată în panoul stâng.\n\n"
                    "(Source audio is already in Romanian. No translation needed. "
                    "The timestamped transcript is displayed in the left panel.)"
                ))
                self.root.after(0, lambda: self.translation_status.set("Nu e necesară (deja română / Not needed)"))
                self.root.after(0, lambda: self.update_status(
                    f"✓ Transcriere completă! Limbă detectată: Română (fără traducere / Transcription complete! Detected language: Romanian, no translation needed)",
                    "green"
                ))
            else:
                # Translate to Romanian - segment by segment to preserve timestamps
                if not self.processing:
                    return
                
                self.root.after(0, lambda: self.update_status(
                    f"Limbă detectată (Detected language): {detected_language}. Se traduce în română... (Translating to Romanian...)",
                    "orange"
                ))
                self.root.after(0, lambda: self.translation_status.set("În curs (In progress...)"))
                
                # Translate each segment individually to preserve timestamps and speaker labels
                translated_segments = []
                total_segments = len(segments)
                
                for idx, segment in enumerate(segments):
                    if not self.processing:
                        return
                    
                    # Update progress
                    progress_msg = f"Se traduce segmentul {idx + 1}/{total_segments}... (Translating segment {idx + 1}/{total_segments}...)"
                    self.root.after(0, lambda msg=progress_msg: self.update_status(msg, "orange"))
                    
                    # Get segment text
                    segment_text = segment['text'].strip()
                    
                    # Translate individual segment
                    if segment_text:
                        translated_text = self.transcriber.translate_to_romanian(
                            segment_text,
                            source_lang=detected_language
                        )
                    else:
                        translated_text = ""
                    
                    # Store translated segment with original timing and speaker info
                    translated_segments.append({
                        'start': segment['start'],
                        'end': segment['end'],
                        'text': translated_text,
                        'speaker': segment.get('speaker')
                    })
                
                if not self.processing:
                    return
                
                # Update translation status based on result
                translation_status = getattr(self.transcriber, 'translation_status', 'Unknown')
                self.root.after(0, lambda: self.translation_status.set(translation_status))
                
                # Store translated segments for later speaker assignment
                if self.diarization_segments:
                    self.diarization_segments['translated'] = translated_segments
                
                # Format translated segments with timestamps (NO speaker labels initially)
                formatted_translation = self._format_text_with_timestamps(translated_segments, speaker_timeline, include_speakers=False)
                
                # Display translation
                self.root.after(0, lambda: self.translation_text.insert(1.0, formatted_translation))
                
                status_msg = f"✓ Transcriere și traducere complete! (Transcription and translation complete!) Limbă detectată (Detected language): {detected_language} | Traducere (Translation): {translation_status}"
                self.root.after(0, lambda: self.update_status(status_msg, "green"))
            
            # Show success message
            self.root.after(0, lambda: messagebox.showinfo(
                "Succes (Success)",
                "Transcriere completată cu succes! Rezultatele sunt afișate în panourile de mai jos.\n\n"
                "(Transcription completed successfully! Results are displayed in the panels below.)"
            ))
            
        except Exception as e:
            error_msg = f"Eroare în timpul procesării (Error during processing): {str(e)}"
            self.logger.error(error_msg)
            self.root.after(0, lambda: self.update_status(error_msg, "red"))
            self.root.after(0, lambda: messagebox.showerror("Eroare (Error)", error_msg))
        
        finally:
            # Reset UI state
            self.root.after(0, self.reset_ui_state)
    
    def reset_ui_state(self):
        """Reset UI state after processing."""
        self.processing = False
        self.process_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.progress.stop()
    
    @staticmethod
    def _format_timestamp(seconds):
        """Format timestamp in seconds to readable format HH:MM:SS."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
    def _format_text_with_timestamps(self, segments, speaker_timeline=None, include_speakers=False):
        """
        Format text with timestamps and optional speaker labels.
        
        Args:
            segments: List of transcription segments from Whisper
            speaker_timeline: Optional dictionary mapping time ranges to speakers (deprecated, kept for compatibility)
            include_speakers: Whether to include speaker labels in the output
        
        Returns:
            Formatted text string with format:
            - Without speaker: [HH:MM:SS -> HH:MM:SS] text
            - With speaker: [HH:MM:SS -> HH:MM:SS] [speaker name] text
        """
        if not segments:
            return ""
        
        formatted_lines = []
        for segment in segments:
            start_time = self._format_timestamp(segment['start'])
            end_time = self._format_timestamp(segment['end'])
            text = segment['text'].strip()
            
            # Only add speaker label if include_speakers is True and speaker info exists
            speaker = segment.get('speaker')
            if include_speakers and speaker:
                # Check if user has assigned a custom name for this speaker
                # speaker_assignments maps "Speaker 1" or "SPEAKER_00" to custom names
                display_speaker = self.speaker_assignments.get(speaker)
                
                if display_speaker:
                    # User entered a custom name for this speaker - show it in brackets
                    formatted_lines.append(f"[{start_time} -> {end_time}] [{display_speaker}] {text}")
                else:
                    # No custom name entered for this speaker - don't add speaker label
                    # Just show timestamp and text
                    formatted_lines.append(f"[{start_time} -> {end_time}] {text}")
            else:
                # No speaker labels requested or no speaker info
                formatted_lines.append(f"[{start_time} -> {end_time}] {text}")
        
        return "\n".join(formatted_lines)
    
    def copy_text(self, text_widget):
        """Copy text from widget to clipboard."""
        try:
            text = text_widget.get(1.0, tk.END).strip()
            if not text:
                messagebox.showwarning("Avertisment (Warning)", "Niciun text de copiat. (No text to copy.)")
                return
            
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            messagebox.showinfo("Succes (Success)", "Text copiat în clipboard! (Text copied to clipboard!)")
        except Exception as e:
            messagebox.showerror("Eroare (Error)", f"Eșec la copierea textului (Failed to copy text): {e}")
    
    def save_text(self, text_widget, text_type):
        """Save text from widget to file."""
        try:
            text = text_widget.get(1.0, tk.END).strip()
            if not text:
                messagebox.showwarning("Avertisment (Warning)", "Niciun text de salvat. (No text to save.)")
                return
            
            # Suggest filename based on original audio file
            if self.selected_file.get():
                base_name = Path(self.selected_file.get()).stem
                if text_type == "translation":
                    default_name = f"{base_name}_translated_ro.txt"
                else:
                    default_name = f"{base_name}_transcription.txt"
            else:
                default_name = f"{text_type}.txt"
            
            # Translate text_type for title
            type_ro = "Traducere (Translation)" if text_type == "translation" else "Transcriere (Transcription)"
            
            filename = filedialog.asksaveasfilename(
                title=f"Salvează {type_ro} (Save {text_type.title()})",
                defaultextension=".txt",
                initialfile=default_name,
                filetypes=[("Fișiere Text (Text Files)", "*.txt"), ("Toate Fișierele (All Files)", "*.*")]
            )
            
            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(text)
                messagebox.showinfo("Succes (Success)", f"Text salvat în (Text saved to):\n{filename}")
        except Exception as e:
            messagebox.showerror("Eroare (Error)", f"Eșec la salvarea textului (Failed to save text): {e}")


def main():
    """Main entry point for the GUI application."""
    root = tk.Tk()
    app = TranscribeROGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
