from __future__ import annotations

import sys
import traceback
from datetime import datetime, timezone

from .config import APP_DIR

LOG_PATH = APP_DIR / "app.log"


def log_message(message: str) -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(f"[{stamp}] {message}\n")


def log_exception(context: str, exc: BaseException) -> None:
    log_message(f"{context}: {exc}\n{traceback.format_exc()}")


def show_fatal_error(exc: BaseException) -> None:
    if sys.platform != "win32":
        return
    import ctypes

    log_exception("fatal", exc)
    ctypes.windll.user32.MessageBoxW(
        None,
        (
            f"Cursor Usage no pudo iniciar.\n\n{exc}\n\n"
            f"Detalle guardado en:\n{LOG_PATH}"
        ),
        "Cursor Usage",
        0x10,  # MB_ICONERROR
    )
