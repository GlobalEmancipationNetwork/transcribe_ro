#!/usr/bin/env python3
"""
Preferences/Settings Dialog System for Transcribe RO

This module provides a comprehensive settings management system including:
- PreferencesDialog: A tabbed dialog for configuring application settings
- SettingsManager: Handles secure storage and retrieval of settings

Settings are stored in a JSON config file in the user's home directory.
The system is designed to be extensible for future settings additions.

Author: transcribe_ro
License: MIT
"""

import os
import json
import logging
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import webbrowser
import threading
from typing import Optional, Dict, Any, Tuple

# Logger for this module
logger = logging.getLogger(__name__)


class SettingsManager:
    """
    Manages application settings storage and retrieval.
    
    Settings are stored in a JSON file in the user's home directory.
    The system supports basic obfuscation for sensitive data like tokens.
    
    Attributes:
        config_dir: Directory where config file is stored
        config_file: Full path to the config file
        settings: Dictionary containing all settings
    """
    
    # Default settings structure - add new settings here for extensibility
    DEFAULT_SETTINGS = {
        "general": {
            "hf_token": "",  # HuggingFace token for speaker diarization
            "auto_load_token": True,  # Automatically set HF_TOKEN env var on startup
        },
        "transcription": {
            "default_model_size": "base",
            "default_device": "auto",
            "default_translation_mode": "auto",
            "force_cpu": False,  # Force CPU to bypass GPU issues
        },
        "ui": {
            "window_width": 1200,
            "window_height": 800,
        },
        "version": "1.0"  # Config version for future migrations
    }
    
    def __init__(self, config_filename: str = ".transcribe_ro_config.json"):
        """
        Initialize the SettingsManager.
        
        Args:
            config_filename: Name of the config file to use
        """
        # Store config in user's home directory
        self.config_dir = Path.home()
        self.config_file = self.config_dir / config_filename
        self.settings = self._load_settings()
    
    def _load_settings(self) -> Dict[str, Any]:
        """
        Load settings from config file.
        
        Returns:
            Dictionary containing settings, or defaults if file doesn't exist
        """
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    # Merge with defaults to ensure all keys exist
                    return self._merge_with_defaults(loaded)
            else:
                logger.info(f"Config file not found, using defaults: {self.config_file}")
                return self.DEFAULT_SETTINGS.copy()
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error loading settings: {e}")
            return self.DEFAULT_SETTINGS.copy()
    
    def _merge_with_defaults(self, loaded: Dict) -> Dict:
        """
        Merge loaded settings with defaults to ensure all keys exist.
        
        Args:
            loaded: Settings loaded from file
            
        Returns:
            Merged settings dictionary
        """
        result = self.DEFAULT_SETTINGS.copy()
        for key, value in loaded.items():
            if key in result:
                if isinstance(value, dict) and isinstance(result[key], dict):
                    result[key].update(value)
                else:
                    result[key] = value
            else:
                result[key] = value
        return result
    
    def save_settings(self) -> bool:
        """
        Save current settings to config file.
        
        Returns:
            True if save was successful, False otherwise
        """
        try:
            # Create directory if it doesn't exist
            self.config_dir.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
            
            # Set file permissions to owner-only read/write (Unix-like systems)
            try:
                os.chmod(self.config_file, 0o600)
            except (OSError, AttributeError):
                pass  # Windows doesn't support chmod the same way
            
            logger.info(f"Settings saved to {self.config_file}")
            return True
        except IOError as e:
            logger.error(f"Error saving settings: {e}")
            return False
    
    def get(self, section: str, key: str, default: Any = None) -> Any:
        """
        Get a setting value.
        
        Args:
            section: Settings section (e.g., 'general', 'transcription')
            key: Setting key within the section
            default: Default value if not found
            
        Returns:
            The setting value, or default if not found
        """
        try:
            return self.settings.get(section, {}).get(key, default)
        except (KeyError, TypeError):
            return default
    
    def set(self, section: str, key: str, value: Any) -> None:
        """
        Set a setting value.
        
        Args:
            section: Settings section
            key: Setting key within the section
            value: Value to set
        """
        if section not in self.settings:
            self.settings[section] = {}
        self.settings[section][key] = value
    
    def get_hf_token(self) -> str:
        """Get the HuggingFace token."""
        return self.get("general", "hf_token", "")
    
    def set_hf_token(self, token: str) -> None:
        """Set the HuggingFace token."""
        self.set("general", "hf_token", token)
    
    def apply_hf_token_to_env(self) -> bool:
        """
        Apply the stored HF token to environment variable.
        
        Returns:
            True if token was set, False if no token available
        """
        token = self.get_hf_token()
        if token:
            os.environ['HF_TOKEN'] = token
            logger.info("HF_TOKEN environment variable set from saved preferences")
            return True
        return False


class PreferencesDialog:
    """
    A professional preferences dialog with tabbed interface.
    
    Features:
    - Tabbed interface for organizing settings
    - HuggingFace token input with show/hide toggle
    - Token validation/testing
    - Save/Cancel buttons
    - Helpful tooltips and links
    """
    
    # HuggingFace URLs
    HF_TOKEN_URL = "https://huggingface.co/settings/tokens"
    PYANNOTE_MODEL_URL = "https://huggingface.co/pyannote/speaker-diarization-3.1"
    
    def __init__(self, parent: tk.Tk, settings_manager: SettingsManager, 
                 on_settings_saved: callable = None):
        """
        Initialize the PreferencesDialog.
        
        Args:
            parent: Parent Tk window
            settings_manager: SettingsManager instance
            on_settings_saved: Callback function called when settings are saved
        """
        self.parent = parent
        self.settings_manager = settings_manager
        self.on_settings_saved = on_settings_saved
        self.dialog = None
        self.show_token = False
        
        # Variables for form fields
        self.hf_token_var = tk.StringVar()
        self.auto_load_token_var = tk.BooleanVar()
        self.default_model_var = tk.StringVar()
        self.default_device_var = tk.StringVar()
        self.default_translation_var = tk.StringVar()
        self.force_cpu_var = tk.BooleanVar()
        
        # Create and show the dialog
        self._create_dialog()
    
    def _create_dialog(self):
        """Create the preferences dialog window."""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("⚙️ Preferințe / Preferences - Transcribe RO")
        self.dialog.geometry("650x580")  # Increased size to fit all content + buttons
        self.dialog.minsize(600, 500)  # Minimum size to ensure buttons are always visible
        self.dialog.resizable(True, True)  # Allow resizing if needed
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Center dialog on parent
        self._center_on_parent()
        
        # Main container with proper structure
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Configure grid for main_frame to keep buttons at bottom
        main_frame.grid_rowconfigure(0, weight=1)  # Notebook expands
        main_frame.grid_rowconfigure(1, weight=0)  # Separator
        main_frame.grid_rowconfigure(2, weight=0)  # Buttons stay fixed
        main_frame.grid_columnconfigure(0, weight=1)
        
        # Create notebook (tabbed interface) - in row 0, expandable
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        
        # Create tabs
        self._create_general_tab()
        self._create_defaults_tab()
        
        # Bottom buttons - in row 1, fixed at bottom
        self._create_buttons(main_frame)
        
        # Load current settings into form
        self._load_current_settings()
        
        # Handle dialog close
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_cancel)
    
    def _center_on_parent(self):
        """Center the dialog on the parent window."""
        self.dialog.update_idletasks()
        parent_x = self.parent.winfo_rootx()
        parent_y = self.parent.winfo_rooty()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()
        
        dialog_width = self.dialog.winfo_width()
        dialog_height = self.dialog.winfo_height()
        
        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2
        
        self.dialog.geometry(f"+{x}+{y}")
    
    def _create_general_tab(self):
        """Create the General settings tab."""
        general_frame = ttk.Frame(self.notebook, padding="15")
        self.notebook.add(general_frame, text="  General  ")
        
        # HuggingFace Token Section
        token_section = ttk.LabelFrame(general_frame, text="🔑 HuggingFace Token", padding="10")
        token_section.pack(fill=tk.X, pady=(0, 15))
        
        # Info label
        info_text = ("Tokenul HuggingFace este necesar pentru recunoașterea vorbitorilor.\n"
                     "The HuggingFace token is required for speaker recognition.")
        ttk.Label(token_section, text=info_text, font=("Helvetica", 9), 
                  foreground="gray").pack(anchor=tk.W, pady=(0, 10))
        
        # Token input row
        token_input_frame = ttk.Frame(token_section)
        token_input_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(token_input_frame, text="Token:").pack(side=tk.LEFT, padx=(0, 10))
        
        self.token_entry = ttk.Entry(token_input_frame, textvariable=self.hf_token_var,
                                     width=45, show="•")
        self.token_entry.pack(side=tk.LEFT, padx=(0, 5))
        
        # Show/Hide button
        self.show_hide_btn = ttk.Button(token_input_frame, text="👁️ Show",
                                        command=self._toggle_token_visibility, width=8)
        self.show_hide_btn.pack(side=tk.LEFT)
        
        # Token status and buttons row
        status_frame = ttk.Frame(token_section)
        status_frame.pack(fill=tk.X, pady=(5, 0))
        
        # Token status indicator
        self.token_status_label = ttk.Label(status_frame, text="", font=("Helvetica", 9))
        self.token_status_label.pack(side=tk.LEFT)
        
        # Buttons frame (right aligned)
        buttons_frame = ttk.Frame(status_frame)
        buttons_frame.pack(side=tk.RIGHT)
        
        # Test Token button
        ttk.Button(buttons_frame, text="🧪 Test Token",
                   command=self._test_token, width=12).pack(side=tk.LEFT, padx=(0, 5))
        
        # Get Token link button
        ttk.Button(buttons_frame, text="🔗 Get Token",
                   command=self._open_hf_token_page, width=12).pack(side=tk.LEFT)
        
        # Auto-load checkbox
        auto_load_frame = ttk.Frame(token_section)
        auto_load_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Checkbutton(auto_load_frame, text="Încarcă automat la pornire (Auto-load on startup)",
                        variable=self.auto_load_token_var).pack(anchor=tk.W)
        
        # Update token status
        self._update_token_status()
        
        # Instructions section
        instructions_section = ttk.LabelFrame(general_frame, text="📋 Instrucțiuni / Instructions", padding="10")
        instructions_section.pack(fill=tk.X)
        
        instructions = (
            "Pentru recunoașterea vorbitorilor / For speaker recognition:\n\n"
            "1. Creați un cont la huggingface.co (gratuit)\n"
            "   Create an account at huggingface.co (free)\n\n"
            "2. Accesați setările token și creați un token nou (Read)\n"
            "   Visit token settings and create a new token (Read)\n\n"
            "3. IMPORTANT: Acceptați termenii modelului pyannote!\n"
            "   IMPORTANT: Accept the pyannote model terms!"
        )
        
        ttk.Label(instructions_section, text=instructions, font=("Helvetica", 9),
                  justify=tk.LEFT).pack(anchor=tk.W, pady=(0, 10))
        
        # Quick links row
        links_frame = ttk.Frame(instructions_section)
        links_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Button(links_frame, text="🔗 Token Settings",
                   command=self._open_hf_token_page, width=16).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(links_frame, text="📄 Accept Model Terms",
                   command=self._open_pyannote_model_page, width=18).pack(side=tk.LEFT)
        
        # Warning note about model terms
        warning_frame = ttk.Frame(instructions_section)
        warning_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Label(warning_frame, 
                  text="⚠️ Dacă token-ul e valid dar diarizarea eșuează, acceptați termenii modelului!\n"
                       "    If token is valid but diarization fails, accept the model terms!",
                  font=("Helvetica", 9), foreground="orange").pack(anchor=tk.W)
    
    def _create_defaults_tab(self):
        """Create the Defaults settings tab."""
        defaults_frame = ttk.Frame(self.notebook, padding="15")
        self.notebook.add(defaults_frame, text="  Valori Implicite / Defaults  ")
        
        # Default settings section
        settings_section = ttk.LabelFrame(defaults_frame, 
                                          text="🎛️ Setări Implicite / Default Settings", padding="10")
        settings_section.pack(fill=tk.X, pady=(0, 15))
        
        # Model size
        row1 = ttk.Frame(settings_section)
        row1.pack(fill=tk.X, pady=5)
        ttk.Label(row1, text="Dimensiune Model (Model Size):", width=30).pack(side=tk.LEFT)
        model_combo = ttk.Combobox(row1, textvariable=self.default_model_var,
                                   values=["tiny", "base", "small", "medium", "large"],
                                   state="readonly", width=15)
        model_combo.pack(side=tk.LEFT, padx=(0, 10))
        ttk.Label(row1, text="(mai mare = mai precis dar mai lent)", font=("Helvetica", 8),
                  foreground="gray").pack(side=tk.LEFT)
        
        # Device
        row2 = ttk.Frame(settings_section)
        row2.pack(fill=tk.X, pady=5)
        ttk.Label(row2, text="Dispozitiv (Device):", width=30).pack(side=tk.LEFT)
        device_combo = ttk.Combobox(row2, textvariable=self.default_device_var,
                                    values=["auto", "cpu", "mps", "cuda"],
                                    state="readonly", width=15)
        device_combo.pack(side=tk.LEFT, padx=(0, 10))
        ttk.Label(row2, text="(auto = detectează cel mai bun)", font=("Helvetica", 8),
                  foreground="gray").pack(side=tk.LEFT)
        
        # Force CPU checkbox
        row3 = ttk.Frame(settings_section)
        row3.pack(fill=tk.X, pady=5)
        ttk.Checkbutton(row3, text="🔧 Forțează CPU (Force CPU - bypass GPU issues)",
                        variable=self.force_cpu_var).pack(side=tk.LEFT)
        
        # Force CPU warning
        force_cpu_warning = ttk.Frame(settings_section)
        force_cpu_warning.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(force_cpu_warning, 
                  text="    ⚠️ Bifați dacă întâmpinați erori MPS/GPU NaN. Revenirea automată este activată implicit.",
                  font=("Helvetica", 8), foreground="orange").pack(side=tk.LEFT)
        
        # Translation mode
        row4 = ttk.Frame(settings_section)
        row4.pack(fill=tk.X, pady=5)
        ttk.Label(row4, text="Mod Traducere (Translation Mode):", width=30).pack(side=tk.LEFT)
        trans_combo = ttk.Combobox(row4, textvariable=self.default_translation_var,
                                   values=["auto", "online", "offline"],
                                   state="readonly", width=15)
        trans_combo.pack(side=tk.LEFT, padx=(0, 10))
        ttk.Label(row4, text="(auto = online mai întâi, apoi offline)", font=("Helvetica", 8),
                  foreground="gray").pack(side=tk.LEFT)
        
        # Note about defaults
        note_frame = ttk.Frame(defaults_frame)
        note_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Label(note_frame, 
                  text="ℹ️ Aceste setări sunt folosite la fiecare transcriere.\n"
                       "    These settings are used for each transcription.",
                  font=("Helvetica", 9), foreground="blue").pack(anchor=tk.W)
    
    def _create_buttons(self, parent):
        """Create the Save/Cancel buttons - always visible at bottom."""
        # Separator line above buttons for visual clarity
        separator = ttk.Separator(parent, orient='horizontal')
        separator.grid(row=1, column=0, sticky="ew", pady=(5, 10))
        
        # Button frame using grid (row 2)
        button_frame = ttk.Frame(parent)
        button_frame.grid(row=2, column=0, sticky="ew", pady=(0, 5))
        
        # Center the buttons
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=0)
        button_frame.grid_columnconfigure(2, weight=0)
        button_frame.grid_columnconfigure(3, weight=1)
        
        # Cancel button
        cancel_btn = ttk.Button(button_frame, text="❌ Anulează (Cancel)",
                                command=self._on_cancel, width=22)
        cancel_btn.grid(row=0, column=1, padx=(0, 15))
        
        # Save button (styled to stand out)
        save_btn = ttk.Button(button_frame, text="💾 Salvează (Save)",
                              command=self._on_save, width=22)
        save_btn.grid(row=0, column=2, padx=(15, 0))
    
    def _load_current_settings(self):
        """Load current settings into form fields."""
        # General tab
        self.hf_token_var.set(self.settings_manager.get("general", "hf_token", ""))
        self.auto_load_token_var.set(self.settings_manager.get("general", "auto_load_token", True))
        
        # Defaults tab
        self.default_model_var.set(self.settings_manager.get("transcription", "default_model_size", "base"))
        self.default_device_var.set(self.settings_manager.get("transcription", "default_device", "auto"))
        self.default_translation_var.set(self.settings_manager.get("transcription", "default_translation_mode", "auto"))
        self.force_cpu_var.set(self.settings_manager.get("transcription", "force_cpu", False))
        
        # Update token status display
        self._update_token_status()
    
    def _toggle_token_visibility(self):
        """Toggle token visibility."""
        self.show_token = not self.show_token
        if self.show_token:
            self.token_entry.config(show="")
            self.show_hide_btn.config(text="🔒 Hide")
        else:
            self.token_entry.config(show="•")
            self.show_hide_btn.config(text="👁️ Show")
    
    def _update_token_status(self):
        """Update the token status indicator."""
        token = self.hf_token_var.get().strip()
        if token:
            # Token is set - show masked indication
            masked = token[:4] + "..." + token[-4:] if len(token) > 8 else "****"
            self.token_status_label.config(text=f"✓ Token setat / Token set ({masked})",
                                          foreground="green")
        else:
            self.token_status_label.config(text="⚠️ Token nesetat / Token not set",
                                          foreground="orange")
    
    def _test_token(self):
        """Test if the HuggingFace token is valid."""
        token = self.hf_token_var.get().strip()
        
        if not token:
            messagebox.showwarning("Test Token",
                                   "Introduceți mai întâi un token.\nPlease enter a token first.")
            return
        
        # Show testing message
        self.token_status_label.config(text="⏳ Se testează... / Testing...",
                                       foreground="blue")
        self.dialog.update()
        
        # Test in a separate thread to avoid UI freeze
        def do_test():
            result, message = self._verify_hf_token(token)
            
            # Update UI in main thread
            self.dialog.after(0, lambda: self._show_test_result(result, message))
        
        threading.Thread(target=do_test, daemon=True).start()
    
    def _verify_hf_token(self, token: str) -> Tuple[bool, str]:
        """
        Verify if the HuggingFace token is valid.
        
        Args:
            token: The HuggingFace token to verify
            
        Returns:
            Tuple of (is_valid, message)
        """
        # First, validate token format
        token = token.strip()
        
        if not token:
            return False, "Token gol / Empty token"
        
        # Check for common token formats (hf_xxx or api_xxx for old format)
        if not (token.startswith('hf_') or token.startswith('api_') or len(token) >= 20):
            return False, ("Format token invalid. Token-ul trebuie să înceapă cu 'hf_'.\n"
                          "Invalid token format. Token should start with 'hf_'.")
        
        try:
            import requests
            
            # Test token by making a simple API call to whoami endpoint
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.get(
                "https://huggingface.co/api/whoami",
                headers=headers,
                timeout=15
            )
            
            if response.status_code == 200:
                user_info = response.json()
                username = user_info.get('name', user_info.get('fullname', 'Unknown'))
                return True, f"Token valid! User: {username}"
            elif response.status_code == 401:
                return False, ("Token invalid sau expirat.\n"
                              "Invalid or expired token.\n\n"
                              "Verificați că ați copiat token-ul complet.\n"
                              "Make sure you copied the full token.")
            elif response.status_code == 403:
                return False, ("Acces interzis. Token-ul nu are permisiunile necesare.\n"
                              "Access forbidden. Token lacks required permissions.")
            else:
                return False, f"Eroare API (API Error): HTTP {response.status_code}"
                
        except ImportError:
            # requests not available, try urllib
            try:
                from urllib.request import Request, urlopen
                from urllib.error import URLError, HTTPError
                import ssl
                
                req = Request(
                    "https://huggingface.co/api/whoami",
                    headers={"Authorization": f"Bearer {token}"}
                )
                
                # Create SSL context
                context = ssl.create_default_context()
                
                with urlopen(req, timeout=15, context=context) as response:
                    if response.status == 200:
                        import json
                        data = json.loads(response.read().decode())
                        username = data.get('name', data.get('fullname', 'Unknown'))
                        return True, f"Token valid! User: {username}"
                    return False, f"Eroare (Error): HTTP {response.status}"
                    
            except HTTPError as e:
                if e.code == 401:
                    return False, ("Token invalid sau expirat.\n"
                                  "Invalid or expired token.\n\n"
                                  "Verificați că ați copiat token-ul complet.\n"
                                  "Make sure you copied the full token.")
                elif e.code == 403:
                    return False, ("Acces interzis. Token-ul nu are permisiunile necesare.\n"
                                  "Access forbidden. Token lacks required permissions.")
                return False, f"Eroare HTTP (HTTP Error): {e.code}"
            except URLError as e:
                reason = str(e.reason) if hasattr(e, 'reason') else str(e)
                return False, (f"Eroare conexiune / Connection error:\n{reason}\n\n"
                              "Verificați conexiunea la internet.\n"
                              "Check your internet connection.")
            except Exception as e:
                return False, f"Eroare (Error): {str(e)}"
        
        except requests.exceptions.Timeout:
            return False, ("Timeout - serverul nu răspunde.\n"
                          "Timeout - server not responding.\n\n"
                          "Încercați din nou mai târziu.\n"
                          "Try again later.")
        except requests.exceptions.ConnectionError:
            return False, ("Eroare conexiune / Connection error.\n\n"
                          "Verificați conexiunea la internet.\n"
                          "Check your internet connection.")
        except Exception as e:
            return False, f"Eroare la verificare (Verification error): {str(e)}"
    
    def _show_test_result(self, is_valid: bool, message: str):
        """Show the token test result."""
        if is_valid:
            self.token_status_label.config(text=f"✓ {message}", foreground="green")
            messagebox.showinfo("Test Token", 
                               f"✓ {message}\n\n"
                               "Token-ul este valid!\n"
                               "The token is valid!\n\n"
                               "Notă: Asigurați-vă că ați acceptat termenii modelului pyannote.\n"
                               "Note: Make sure you've accepted the pyannote model terms.")
        else:
            self.token_status_label.config(text="✗ Test eșuat / Test failed", foreground="red")
            # Show error with additional help
            help_text = ("\n\n--- Ajutor / Help ---\n"
                        "• Verificați că token-ul este copiat complet\n"
                        "  Check that the token is fully copied\n"
                        "• Asigurați-vă că token-ul are permisiuni 'Read'\n"
                        "  Make sure the token has 'Read' permissions\n"
                        "• Puteți salva token-ul oricum și va fi verificat la utilizare\n"
                        "  You can save the token anyway and it will be verified when used")
            messagebox.showerror("Test Token", f"✗ {message}{help_text}")
    
    def _open_hf_token_page(self):
        """Open HuggingFace token page in browser."""
        try:
            webbrowser.open(self.HF_TOKEN_URL)
        except Exception as e:
            messagebox.showerror("Error", 
                                f"Nu s-a putut deschide browserul.\nCould not open browser.\n\n{e}")
    
    def _open_pyannote_model_page(self):
        """Open pyannote model page in browser to accept terms."""
        try:
            webbrowser.open(self.PYANNOTE_MODEL_URL)
        except Exception as e:
            messagebox.showerror("Error", 
                                f"Nu s-a putut deschide browserul.\nCould not open browser.\n\n{e}")
    
    def _on_save(self):
        """Handle save button click."""
        # Clean and validate token format (but don't require API validation)
        token = self.hf_token_var.get().strip()
        
        # Basic format check (warning only, not blocking)
        token_warning = ""
        if token and not (token.startswith('hf_') or token.startswith('api_')):
            token_warning = ("\n\n⚠️ Token-ul nu pare să aibă formatul corect (hf_...).\n"
                            "   Token doesn't seem to have the correct format (hf_...).\n"
                            "   Va fi salvat oricum / Will be saved anyway.")
        
        # Save all settings
        self.settings_manager.set("general", "hf_token", token)
        self.settings_manager.set("general", "auto_load_token", self.auto_load_token_var.get())
        self.settings_manager.set("transcription", "default_model_size", self.default_model_var.get())
        self.settings_manager.set("transcription", "default_device", self.default_device_var.get())
        self.settings_manager.set("transcription", "default_translation_mode", self.default_translation_var.get())
        self.settings_manager.set("transcription", "force_cpu", self.force_cpu_var.get())
        
        # Save to file
        if self.settings_manager.save_settings():
            # Apply HF token to environment if set
            if token:
                self.settings_manager.apply_hf_token_to_env()
            
            success_msg = ("Setările au fost salvate cu succes!\n"
                          "Settings saved successfully!")
            
            if token:
                success_msg += ("\n\nToken-ul va fi verificat când folosiți recunoașterea vorbitorilor.\n"
                               "The token will be verified when you use speaker recognition.")
            
            success_msg += token_warning
            
            messagebox.showinfo("Salvat / Saved", success_msg)
            
            # Call callback if provided
            if self.on_settings_saved:
                self.on_settings_saved()
            
            self.dialog.destroy()
        else:
            messagebox.showerror("Eroare / Error",
                                "Nu s-au putut salva setările.\n"
                                "Could not save settings.")
    
    def _on_cancel(self):
        """Handle cancel button click."""
        self.dialog.destroy()


def show_preferences_dialog(parent: tk.Tk, settings_manager: SettingsManager,
                           on_settings_saved: callable = None) -> PreferencesDialog:
    """
    Show the preferences dialog.
    
    Args:
        parent: Parent Tk window
        settings_manager: SettingsManager instance
        on_settings_saved: Callback when settings are saved
        
    Returns:
        PreferencesDialog instance
    """
    return PreferencesDialog(parent, settings_manager, on_settings_saved)
