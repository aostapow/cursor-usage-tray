# -*- mode: python ; coding: utf-8 -*-
import os

block_cipher = None

_runtime_tmp = os.path.join(
    os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
    "cursor-usage-tray",
    "_runtime-float",
)

a = Analysis(
    ["app_float.py"],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=["pyi_rth_tk.py"],
    excludes=["pystray"],
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
    name="cursor-usage-float",
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
    name="cursor-usage-float",
)
