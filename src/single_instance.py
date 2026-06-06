from __future__ import annotations

import ctypes
import sys

_MUTEX_NAME = "Global\\cursor-usage-tray-v1"


def ensure_single_instance() -> bool:
    """Return False if another instance is already running."""
    kernel32 = ctypes.windll.kernel32
    mutex = kernel32.CreateMutexW(None, True, _MUTEX_NAME)
    if kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        if mutex:
            kernel32.CloseHandle(mutex)
        return False
    return True


def _notify_already_running() -> None:
    if sys.platform != "win32":
        return
    ctypes.windll.user32.MessageBoxW(
        None,
        (
            "Cursor Usage ya está en ejecución.\n\n"
            "Buscá el icono en la bandeja del sistema (junto al reloj) "
            "o el monto flotante en pantalla.\n\n"
            "Si no lo ves, cerrá la otra copia desde el Administrador de tareas."
        ),
        "Cursor Usage",
        0x40,  # MB_ICONINFORMATION
    )


def exit_if_already_running() -> None:
    if not ensure_single_instance():
        _notify_already_running()
        sys.exit(0)
