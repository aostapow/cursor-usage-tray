# -*- mode: python ; coding: utf-8 -*-
import os

block_cipher = None

_runtime_tmp = os.path.join(
    os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
    "cursor-usage-tray",
    "_runtime-tray",
)

a = Analysis(
    ["app_tray.py"],
    pathex=[],
    binaries=[],
    datas=[("assets/tray-icon.png", "assets")],
    hiddenimports=[
        "pystray._win32",
        "PIL.Image",
        "PIL.ImageDraw",
        "PIL.ImageFont",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="cursor-usage-tray",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=_runtime_tmp,
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
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="cursor-usage-tray",
)
