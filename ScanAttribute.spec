# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['scan_attribute/main.py'],
    pathex=[],
    binaries=[],
    datas=[('scan_attribute/resources', 'resources'), ('scan_attribute/resources', 'scan_attribute/resources')],
    hiddenimports=['openpyxl', 'fitz', 'cv2', 'PIL', 'pyzbar'],
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
