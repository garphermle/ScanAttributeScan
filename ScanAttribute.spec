# -*- mode: python ; coding: utf-8 -*-
import os
import sys

datas = [
    ('scan_attribute/resources', 'scan_attribute/resources'),
    ('scan_attribute/resources', 'resources')
]

hiddenimports = [
    'openpyxl',
    'openpyxl.cell',
    'openpyxl.styles',
    'openpyxl.reader.excel',
    'pypdfium2',
    'fitz',
    'cv2',
    'PIL',
    'PIL.Image',
    'pyzbar',
    'rapidocr_onnxruntime',
    'onnxruntime',
    'numpy',
    'PySide6',
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
]

a = Analysis(
    ['scan_attribute/main.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
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
    [],
    exclude_binaries=True,
    name='ScanAttribute',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ScanAttribute',
)
