# -*- mode: python ; coding: utf-8 -*-
import whisper
import os

# Locate whisper's assets
whisper_path = os.path.dirname(whisper.__file__)
whisper_assets = os.path.join(whisper_path, 'assets')

a = Analysis(
    ['transcribe_ro_gui.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets', 'assets'),                    # Your app's assets (logo, etc.)
        (whisper_assets, 'whisper/assets'),      # Whisper's mel_filters.npz
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Transcribe_RO',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/transcribe_ro.icns',
)
app = BUNDLE(
    exe,
    name='Transcribe_RO.app',
    icon='assets/transcribe_ro.icns',
    bundle_identifier=None,
)