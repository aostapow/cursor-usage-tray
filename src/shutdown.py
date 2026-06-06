from __future__ import annotations

import ctypes
from ctypes import wintypes

from .paths import SHUTDOWN_EVENT_NAME

kernel32 = ctypes.windll.kernel32

EVENT_MODIFY_STATE = 0x0002
SYNCHRONIZE = 0x001000
WAIT_OBJECT_0 = 0x00000000
INFINITE = 0xFFFFFFFF


def create_shutdown_event() -> int | None:
    handle = kernel32.CreateEventW(None, True, False, SHUTDOWN_EVENT_NAME)
    if not handle:
        return None
    return int(handle)


def open_shutdown_event() -> int | None:
    handle = kernel32.OpenEventW(EVENT_MODIFY_STATE | SYNCHRONIZE, False, SHUTDOWN_EVENT_NAME)
    if not handle:
        return None
    return int(handle)


def signal_shutdown() -> bool:
    handle = open_shutdown_event()
    if not handle:
        handle = create_shutdown_event()
    if not handle:
        return False
    try:
        return bool(kernel32.SetEvent(handle))
    finally:
        kernel32.CloseHandle(handle)


def reset_shutdown_event() -> None:
    handle = open_shutdown_event()
    if not handle:
        handle = create_shutdown_event()
    if not handle:
        return
    try:
        kernel32.ResetEvent(handle)
    finally:
        kernel32.CloseHandle(handle)


def wait_shutdown(timeout_ms: int = 1000) -> bool:
    handle = open_shutdown_event()
    if not handle:
        return False
    try:
        result = kernel32.WaitForSingleObject(handle, wintypes.DWORD(timeout_ms))
        return result == WAIT_OBJECT_0
    finally:
        kernel32.CloseHandle(handle)


def close_handle(handle: int | None) -> None:
    if handle:
        kernel32.CloseHandle(handle)
