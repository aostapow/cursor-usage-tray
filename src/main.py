from __future__ import annotations

import argparse
import sys


def _ensure_console() -> None:
    """Allow --show-config output when running as a windowed PyInstaller exe."""
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


def _report_fatal_error(exc: BaseException) -> None:
    from .config import APP_DIR

    APP_DIR.mkdir(parents=True, exist_ok=True)
    log_path = APP_DIR / "app.log"
    log_path.write_text(f"{type(exc).__name__}: {exc}\n", encoding="utf-8")
    if sys.platform == "win32":
        import ctypes

        ctypes.windll.user32.MessageBoxW(
            None,
            f"No se pudo iniciar Cursor Usage.\n\n{type(exc).__name__}: {exc}\n\nLog: {log_path}",
            "Cursor Usage",
            0x10,  # MB_ICONERROR
        )


def main() -> int:
    from .auth import resolve_cursor_account_email, resolve_session_token
    from .config import AppConfig, CONFIG_PATH
    from .single_instance import exit_if_already_running
    from .startup import sync_startup_with_config
    from .tray import UsageTrayApp

    args = _parse_args()
    if not args.show_config:
        exit_if_already_running()

    config = AppConfig.load()
    sync_startup_with_config(config.start_with_windows)

    if args.show_config:
        _ensure_console()
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
        text = "\n".join(lines)
        print(text)
        _pause_before_exit(text)
        return 0

    def get_token() -> tuple[str | None, str]:
        return resolve_session_token()

    try:
        app = UsageTrayApp(config=config, get_token=get_token)
        app.run()
    except Exception as exc:  # noqa: BLE001
        _report_fatal_error(exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
