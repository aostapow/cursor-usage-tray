from __future__ import annotations

import os
import sys
import winreg
from pathlib import Path

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_RUN_NAME = "cursor-usage-tray"


def app_executable_path() -> str:
    if getattr(sys, "frozen", False):
        return str(Path(sys.executable).resolve())
    return str((Path(__file__).resolve().parent.parent / "run.ps1").resolve())


def is_startup_enabled() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, APP_RUN_NAME)
            return bool(str(value).strip())
    except OSError:
        return False


def set_startup_enabled(enabled: bool) -> None:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            exe = app_executable_path()
            if exe.lower().endswith(".ps1"):
                command = (
                    f'powershell.exe -WindowStyle Hidden -ExecutionPolicy Bypass '
                    f'-File "{exe}"'
                )
            else:
                command = f'"{exe}"'
            winreg.SetValueEx(key, APP_RUN_NAME, 0, winreg.REG_SZ, command)
        else:
            try:
                winreg.DeleteValue(key, APP_RUN_NAME)
            except FileNotFoundError:
                pass


def sync_startup_with_config(enabled: bool) -> None:
    if enabled and not is_startup_enabled():
        set_startup_enabled(True)
    elif not enabled and is_startup_enabled():
        set_startup_enabled(False)
