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
        DIARIZATION_AVAILABLE
    )
except ImportError:
    print("Error: Could not import transcribe_ro module.")
    print("Make sure transcribe_ro.py is in the same directory.")
    sys.exit(1)


class TranscribeROGUI:
    """Main GUI application class for Transcribe RO."""
    
    def __init__(self, root):
        """Initialize the GUI application."""
        self.root = root
        self.root.title("Transcribe RO - Transcriere Audio și Traducere (Audio Transcription & Translation)")
        self.root.geometry("1200x800")
        
        # Initialize settings manager and load saved settings
        self.settings_manager = None
        if PREFERENCES_AVAILABLE:
            self.settings_manager = SettingsManager()
            self._apply_saved_settings()
        
        # Configure window icon (if available)
        try:
            # Add window icon if available
            pass
        except:
            pass
        
        # Variables
        self.selected_file = tk.StringVar()
        self.source_language = tk.StringVar(value="ro")  # Romanian as default
        self.model_size = tk.StringVar(value="base")
        self.device_type = tk.StringVar(value="auto")
        self.force_cpu = tk.BooleanVar(value=False)
        self.translation_mode = tk.StringVar(value="auto")
        self.translation_status = tk.StringVar(value="Neînceput (Not started)")
        self.speaker1_name = tk.StringVar(value="")  # Speaker 1 name
        self.speaker2_name = tk.StringVar(value="")  # Speaker 2 name
        self.processing = False
        self.transcriber = None
        self.current_result = None  # Store the transcription result with segments
        
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
        
        # Supported audio formats
        self.audio_formats = [
            ("Audio Files", "*.mp3 *.wav *.m4a *.flac *.ogg *.wma *.aac *.opus"),
            ("MP3 Files", "*.mp3"),
            ("WAV Files", "*.wav"),
            ("M4A Files", "*.m4a"),
            ("FLAC Files", "*.flac"),
            ("All Files", "*.*")
        ]
        
        # Setup logging
        setup_logging(debug=False)
        self.logger = logging.getLogger(__name__)
        
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
            return
        
        # Apply HF_TOKEN to environment variable if auto-load is enabled
        auto_load = self.settings_manager.get("general", "auto_load_token", True)
        if auto_load:
            if self.settings_manager.apply_hf_token_to_env():
                self.logger.info("HF_TOKEN loaded from saved preferences")
    
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
        # Update speaker recognition status
        self._update_speaker_status()
    
    def _update_speaker_status(self):
        """Update the speaker recognition status indicator."""
        if not hasattr(self, 'speaker_status_label'):
            return
        
        # Re-check diarization requirements (which will now include the new HF_TOKEN)
        is_available, error_msg = check_diarization_requirements()
        
        if is_available:
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
        
        # Settings and Language selection section (side by side)
        self.create_settings_and_language_section(main_frame)
        
        # Speaker recognition section
        self.create_speaker_section(main_frame)
        
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
        header_frame.columnconfigure(0, weight=1)
        
        # Left side: Title and subtitle
        title_frame = ttk.Frame(header_frame)
        title_frame.grid(row=0, column=0, sticky=tk.W)
        
        title_label = ttk.Label(
            title_frame,
            text="🎙️ Transcribe RO",
            font=("Helvetica", 20, "bold")
        )
        title_label.grid(row=0, column=0, sticky=tk.W)
        
        subtitle_label = ttk.Label(
            title_frame,
            text="Transcriere Audio și Traducere în Română (Audio Transcription & Translation to Romanian)",
            font=("Helvetica", 10)
        )
        subtitle_label.grid(row=1, column=0, sticky=tk.W)
        
        # Right side: Settings button
        if PREFERENCES_AVAILABLE:
            settings_btn = ttk.Button(
                header_frame,
                text="⚙️ Preferințe (Settings)",
                command=self.open_preferences,
                width=22
            )
            settings_btn.grid(row=0, column=1, sticky=tk.E, padx=(10, 0))
    
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
    
    def create_settings_and_language_section(self, parent):
        """Create the settings and language selection sections side by side."""
        # Container for both sections
        container = ttk.Frame(parent)
        container.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        container.columnconfigure(0, weight=1)
        container.columnconfigure(1, weight=1)
        
        # Left side: Settings
        settings_frame = ttk.LabelFrame(container, text="Setări (Settings)", padding="10")
        settings_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        
        # Model size selection
        ttk.Label(settings_frame, text="Dimensiune Model (Model Size):").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        model_combo = ttk.Combobox(
            settings_frame,
            textvariable=self.model_size,
            values=["tiny", "base", "small", "medium", "large"],
            state="readonly",
            width=15
        )
        model_combo.grid(row=0, column=1, sticky=tk.W, padx=(0, 10))
        
        ttk.Label(
            settings_frame,
            text="(mai mare = mai precis dar mai lent)",
            font=("Helvetica", 8)
        ).grid(row=0, column=2, sticky=tk.W)
        
        # Device selection
        ttk.Label(settings_frame, text="Dispozitiv (Device):").grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        device_combo = ttk.Combobox(
            settings_frame,
            textvariable=self.device_type,
            values=["auto", "cpu", "mps", "cuda"],
            state="readonly",
            width=15
        )
        device_combo.grid(row=1, column=1, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        
        ttk.Label(
            settings_frame,
            text="(auto = detectează cel mai bun)",
            font=("Helvetica", 8)
        ).grid(row=1, column=2, sticky=tk.W, pady=(10, 0))
        
        # Force CPU checkbox
        force_cpu_check = ttk.Checkbutton(
            settings_frame,
            text="🔧 Forțează CPU (Force CPU - bypass GPU issues)",
            variable=self.force_cpu
        )
        force_cpu_check.grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=(10, 0))
        
        ttk.Label(
            settings_frame,
            text="⚠️ Bifați dacă întâmpinați erori MPS/GPU NaN.",
            font=("Helvetica", 8),
            foreground="orange"
        ).grid(row=3, column=0, columnspan=3, sticky=tk.W)
        
        # Translation mode selection
        ttk.Label(settings_frame, text="Mod Traducere (Translation Mode):").grid(row=4, column=0, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        translation_combo = ttk.Combobox(
            settings_frame,
            textvariable=self.translation_mode,
            values=["auto", "online", "offline"],
            state="readonly",
            width=15
        )
        translation_combo.grid(row=4, column=1, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        
        ttk.Label(
            settings_frame,
            text="(auto = online mai întâi, apoi offline)",
            font=("Helvetica", 8)
        ).grid(row=4, column=2, sticky=tk.W, pady=(10, 0))
        
        # Translation status label
        ttk.Label(settings_frame, text="Status Traducere:").grid(row=5, column=0, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        self.translation_status_label = ttk.Label(
            settings_frame,
            textvariable=self.translation_status,
            font=("Helvetica", 9, "bold"),
            foreground="gray"
        )
        self.translation_status_label.grid(row=5, column=1, columnspan=2, sticky=tk.W, pady=(10, 0))
        
        # Right side: Language Selection
        lang_frame = ttk.LabelFrame(container, text="Limbă Sursă (Source Language)", padding="10")
        lang_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0))
        
        # Create a scrollable frame for language options
        canvas = tk.Canvas(lang_frame, height=120)
        scrollbar = ttk.Scrollbar(lang_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Add language radio buttons in a grid
        row, col = 0, 0
        max_cols = 3
        
        for lang_code, lang_name in self.languages.items():
            rb = ttk.Radiobutton(
                scrollable_frame,
                text=lang_name,
                variable=self.source_language,
                value=lang_code
            )
            rb.grid(row=row, column=col, sticky=tk.W, padx=10, pady=2)
            
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
        
        canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        lang_frame.columnconfigure(0, weight=1)
        
        # Info label
        info_label = ttk.Label(
            lang_frame,
            text="ℹ️ Româna este selectată implicit. Dacă audio-ul este deja în română, se va afișa doar transcrierea.",
            font=("Helvetica", 9),
            foreground="blue"
        )
        info_label.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(10, 0))
    
    def create_speaker_section(self, parent):
        """Create the speaker recognition section."""
        speaker_frame = ttk.LabelFrame(parent, text="🎤 Recunoaștere Vorbitori (Speaker Recognition) - Opțional", padding="10")
        speaker_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        speaker_frame.columnconfigure(1, weight=1)
        speaker_frame.columnconfigure(3, weight=1)
        
        # Speaker 1 name
        ttk.Label(speaker_frame, text="Nume Vorbitor 1 (Speaker 1 Name):").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        speaker1_entry = ttk.Entry(
            speaker_frame,
            textvariable=self.speaker1_name,
            width=20
        )
        speaker1_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 20))
        
        # Speaker 2 name
        ttk.Label(speaker_frame, text="Nume Vorbitor 2 (Speaker 2 Name):").grid(row=0, column=2, sticky=tk.W, padx=(0, 10))
        speaker2_entry = ttk.Entry(
            speaker_frame,
            textvariable=self.speaker2_name,
            width=20
        )
        speaker2_entry.grid(row=0, column=3, sticky=(tk.W, tk.E))
        
        # Check diarization availability and show appropriate status
        is_available, error_msg = check_diarization_requirements()
        
        if is_available:
            status_text = "✓ Recunoașterea vorbitorilor este disponibilă (Speaker recognition is available)"
            status_color = "green"
        elif not DIARIZATION_AVAILABLE:
            status_text = "⚠️ pyannote.audio nu este instalat (pyannote.audio not installed)"
            status_color = "orange"
        else:
            # HF_TOKEN missing - reference preferences
            status_text = "⚠️ HF_TOKEN lipsește - folosiți Preferințe (HF_TOKEN missing - use Preferences)"
            status_color = "orange"
        
        # Status row with label and optional link button
        status_row = ttk.Frame(speaker_frame)
        status_row.grid(row=1, column=0, columnspan=4, sticky=tk.W, pady=(10, 0))
        
        # Status label
        self.speaker_status_label = ttk.Label(
            status_row,
            text=status_text,
            font=("Helvetica", 8),
            foreground=status_color
        )
        self.speaker_status_label.pack(side=tk.LEFT)
        
        # Add clickable link to HuggingFace token page (for setting up model access)
        if PREFERENCES_AVAILABLE:
            hf_link = ttk.Label(
                status_row,
                text="  |  Includeți numele a doi vorbitori pentru a activa recunoașterea vorbitorilor: ",
                font=("Helvetica", 8),
                foreground="gray"
            )
            hf_link.pack(side=tk.LEFT)
            
            hf_link_btn = ttk.Label(
                status_row,
                text="NecessitățiToken HuggingFace (HF_TOKEN)",
                font=("Helvetica", 8, "underline"),
                foreground="blue",
                cursor="hand2"
            )
            hf_link_btn.pack(side=tk.LEFT)
            hf_link_btn.bind("<Button-1>", lambda e: self.open_preferences())
    
    def create_control_buttons(self, parent):
        """Create control buttons."""
        button_frame = ttk.Frame(parent)
        button_frame.grid(row=4, column=0, columnspan=2, pady=(0, 10))
        
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
        progress_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
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
        status_frame.grid(row=6, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
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
        results_frame.grid(row=7, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 0))
        
        # Configure grid weights for resizing - give more weight to results section
        parent.rowconfigure(7, weight=3)  # Give results section 3x weight
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
        
        # Clear previous results
        self.original_text.delete(1.0, tk.END)
        self.translation_text.delete(1.0, tk.END)
        
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
            
            # Handle force CPU option
            device_to_use = 'cpu' if self.force_cpu.get() else self.device_type.get()
            if self.force_cpu.get():
                self.logger.info("Force CPU option enabled: GPU acceleration disabled")
            
            self.transcriber = AudioTranscriber(
                model_name=self.model_size.get(),
                device=device_to_use,
                verbose=True,
                debug=False,
                translation_mode=self.translation_mode.get()
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
            
            # Perform speaker diarization if both speaker names are provided
            speaker_timeline = None
            diarization_status = None
            speaker1 = self.speaker1_name.get().strip()
            speaker2 = self.speaker2_name.get().strip()
            
            if speaker1 and speaker2:
                self.logger.info(f"Speaker names provided: '{speaker1}' and '{speaker2}'")
                
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
                            "3. Set environment variable: export HF_TOKEN=your_token\n"
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
                    
                    # Call diarization with debug enabled to get detailed logs
                    speaker_timeline, diarization_status = perform_speaker_diarization(
                        self.selected_file.get(),
                        speaker_names=[speaker1, speaker2],
                        debug=True  # Enable debug for detailed logging
                    )
                    
                    # Add speaker labels to segments if diarization succeeded
                    if speaker_timeline:
                        self.logger.info(f"✓ {diarization_status}")
                        self.root.after(0, lambda msg=f"✓ {diarization_status}": self.update_status(msg, "green"))
                        
                        for segment in segments:
                            segment_mid = (segment['start'] + segment['end']) / 2
                            speaker = get_speaker_for_timestamp(speaker_timeline, segment_mid)
                            segment['speaker'] = speaker if speaker else "Unknown"
                        
                        self.logger.info(f"Speaker labels assigned to {len(segments)} segments")
                    else:
                        # Diarization failed after passing pre-checks
                        self.logger.warning(f"Speaker diarization failed: {diarization_status}")
                        self.root.after(0, lambda msg=f"⚠️ {diarization_status}": self.update_status(msg, "orange"))
                        self.root.after(0, lambda: messagebox.showwarning(
                            "Speaker Recognition Failed",
                            f"Speaker recognition encountered an error:\n\n{diarization_status}\n\n"
                            "Transcription will continue without speaker labels."
                        ))
            elif speaker1 or speaker2:
                # Only one speaker name provided
                self.logger.info("Only one speaker name provided - need both for diarization")
                self.root.after(0, lambda: self.update_status(
                    "ℹ️ Ambele nume de vorbitori sunt necesare pentru diarizare (Both speaker names required)", 
                    "blue"
                ))
            
            # Format original transcript with timestamps and speaker labels
            formatted_transcript = self._format_text_with_timestamps(segments, speaker_timeline)
            
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
                self.root.after(0, lambda: self.translation_status_label.config(foreground="green"))
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
                self.root.after(0, lambda: self.translation_status_label.config(foreground="orange"))
                
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
                
                # Set color based on status
                if "Failed" in translation_status:
                    self.root.after(0, lambda: self.translation_status_label.config(foreground="red"))
                elif translation_status == "Online":
                    self.root.after(0, lambda: self.translation_status_label.config(foreground="blue"))
                elif translation_status == "Offline":
                    self.root.after(0, lambda: self.translation_status_label.config(foreground="green"))
                else:
                    self.root.after(0, lambda: self.translation_status_label.config(foreground="gray"))
                
                # Format translated segments with timestamps and speaker labels (same format as original)
                formatted_translation = self._format_text_with_timestamps(translated_segments, speaker_timeline)
                
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
    
    def _format_text_with_timestamps(self, segments, speaker_timeline=None):
        """
        Format text with timestamps and optional speaker labels.
        
        Args:
            segments: List of transcription segments from Whisper
            speaker_timeline: Optional dictionary mapping time ranges to speakers
        
        Returns:
            Formatted text string
        """
        if not segments:
            return ""
        
        formatted_lines = []
        for segment in segments:
            start_time = self._format_timestamp(segment['start'])
            end_time = self._format_timestamp(segment['end'])
            text = segment['text'].strip()
            
            # Add speaker label if available
            speaker = segment.get('speaker')
            if speaker:
                formatted_lines.append(f"[{start_time} -> {end_time}] [Speaker: {speaker}] {text}")
            else:
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
