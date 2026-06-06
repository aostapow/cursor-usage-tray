from __future__ import annotations

import argparse
import sys


def _ensure_console() -> None:
    if sys.platform != "win32" or getattr(sys, "frozen", False) is False:
        return
    import ctypes

    kernel32 = ctypes.windll.kernel32
    if kernel32.GetConsoleWindow():
        return
    kernel32.AllocConsole()
    sys.stdout = open("CONOUT$", "w", encoding="utf-8")  # noqa: SIM115
    sys.stderr = open("CONOUT$", "w", encoding="utf-8")  # noqa: SIM115


def _parse_args() -> argparse.Namespace:
    from .__version__ import __version__

    parser = argparse.ArgumentParser(description="Cursor usage tray for Windows")
    parser.add_argument("--tray", action="store_true", help="Iniciar supervisor de bandeja")
    parser.add_argument("--float", action="store_true", help="Iniciar monto flotante")
    parser.add_argument(
        "--show-config",
        action="store_true",
        help="Mostrar configuración y si Cursor tiene sesión activa",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser.parse_args()


def _pause_before_exit(message: str) -> None:
    if getattr(sys, "frozen", False):
        import ctypes

        ctypes.windll.user32.MessageBoxW(None, message, "Cursor Usage", 0x40)
        return
    if sys.stdin is not None and sys.stdin.isatty():
        input("\nPresioná Enter para cerrar...")


def _show_config() -> int:
    from .auth import resolve_cursor_account_email, resolve_session_token
    from .config import CONFIG_PATH, AppConfig

    _ensure_console()
    config = AppConfig.load()
    token, source = resolve_session_token()
    email = resolve_cursor_account_email()
    lines = [
        f"Config: {CONFIG_PATH}",
        f"Sesión Cursor: {'activa' if token else 'no detectada'}",
        f"Detalle: {source}",
    ]
    if email:
        lines.append(f"Cuenta: {email}")
    lines.append(f"Refresh: cada {config.refresh_interval_seconds}s")
    lines.append(f"Alternancia label: cada {config.label_alternate_seconds}s")
    text = "\n".join(lines)
    print(text)
    _pause_before_exit(text)
    return 0


def main() -> int:
    args = _parse_args()

    if args.show_config:
        return _show_config()

    if args.float:
        from .float_main import main as float_main

        return float_main()

    from .tray_main import main as tray_main

    return tray_main()


if __name__ == "__main__":
    sys.exit(main())
