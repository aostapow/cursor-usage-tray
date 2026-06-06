from __future__ import annotations

import os
import sys
from pathlib import Path

from .config import APP_DIR

INSTALL_DIR = APP_DIR / "app"
FLOAT_DIR = INSTALL_DIR / "float"
UPDATES_DIR = APP_DIR / "updates"
STATE_PATH = APP_DIR / "state.json"

FLOAT_EXE_NAME = "cursor-usage-float.exe"
TRAY_EXE_NAME = "cursor-usage-tray.exe"
INICIAR_CMD_NAME = "Iniciar.cmd"

SHUTDOWN_EVENT_NAME = "Global\\cursor-usage-float-shutdown"


def installed_in_app_dir() -> bool:
    if not getattr(sys, "frozen", False):
        return False
    try:
        return Path(sys.executable).resolve().parent.resolve() == INSTALL_DIR.resolve()
    except OSError:
        return False


def tray_executable() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve()
    return Path(__file__).resolve().parent.parent / TRAY_EXE_NAME


def float_executable() -> Path:
    if getattr(sys, "frozen", False):
        tray_dir = Path(sys.executable).resolve().parent
        candidate = tray_dir / "float" / FLOAT_EXE_NAME
        if candidate.exists():
            return candidate
        sibling = tray_dir / FLOAT_EXE_NAME
        if sibling.exists():
            return sibling
    return Path(__file__).resolve().parent.parent / "dist" / "cursor-usage-tray" / "float" / FLOAT_EXE_NAME


def iniciar_cmd_path() -> Path:
    return INSTALL_DIR / INICIAR_CMD_NAME


def float_launch_command(*extra: str) -> list[str]:
    exe = float_executable()
    if getattr(sys, "frozen", False) and exe.exists():
        return [str(exe), *extra]
    python = sys.executable
    return [python, "-m", "src.float_main", *extra]


def settings_launch_command() -> list[str]:
    return float_launch_command("--settings")


def ensure_app_dirs() -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    UPDATES_DIR.mkdir(parents=True, exist_ok=True)
