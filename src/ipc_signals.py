from __future__ import annotations

import os

from .config import APP_DIR, CONFIG_PATH

RESET_LABEL_FLAG = APP_DIR / "reset_label_position.flag"
REFRESH_EVENT_NAME = "Global\\cursor-usage-float-refresh"


def config_mtime() -> float:
    if not CONFIG_PATH.exists():
        return 0.0
    try:
        return CONFIG_PATH.stat().st_mtime
    except OSError:
        return 0.0


def request_label_reset() -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    RESET_LABEL_FLAG.write_text("", encoding="utf-8")


def consume_label_reset_request() -> bool:
    if not RESET_LABEL_FLAG.exists():
        return False
    try:
        RESET_LABEL_FLAG.unlink(missing_ok=True)
    except OSError:
        pass
    return True


def _pulse_event(name: str) -> bool:
    if os.name != "nt":
        return False
    import ctypes

    kernel32 = ctypes.windll.kernel32
    EVENT_MODIFY_STATE = 0x0002
    handle = kernel32.OpenEventW(EVENT_MODIFY_STATE, False, name)
    if not handle:
        handle = kernel32.CreateEventW(None, True, False, name)
    if not handle:
        return False
    try:
        return bool(kernel32.SetEvent(handle))
    finally:
        kernel32.CloseHandle(handle)


def _wait_event(name: str, timeout_ms: int) -> bool:
    if os.name != "nt":
        return False
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.windll.kernel32
    EVENT_MODIFY_STATE = 0x0002
    SYNCHRONIZE = 0x001000
    WAIT_OBJECT_0 = 0x00000000
    handle = kernel32.OpenEventW(EVENT_MODIFY_STATE | SYNCHRONIZE, False, name)
    if not handle:
        return False
    try:
        result = kernel32.WaitForSingleObject(handle, wintypes.DWORD(timeout_ms))
        if result == WAIT_OBJECT_0:
            kernel32.ResetEvent(handle)
            return True
        return False
    finally:
        kernel32.CloseHandle(handle)


def signal_refresh() -> bool:
    return _pulse_event(REFRESH_EVENT_NAME)


def wait_refresh(timeout_ms: int = 500) -> bool:
    return _wait_event(REFRESH_EVENT_NAME, timeout_ms)
