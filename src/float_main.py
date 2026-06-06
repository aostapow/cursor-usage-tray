from __future__ import annotations

import argparse
import sys


def _report_fatal_error(exc: BaseException, *, component: str) -> None:
    from .config import APP_DIR

    APP_DIR.mkdir(parents=True, exist_ok=True)
    log_path = APP_DIR / "float.log"
    log_path.write_text(f"{type(exc).__name__}: {exc}\n", encoding="utf-8")
    if sys.platform == "win32":
        import ctypes

        ctypes.windll.user32.MessageBoxW(
            None,
            f"No se pudo iniciar Cursor Usage ({component}).\n\n{type(exc).__name__}: {exc}\n\nLog: {log_path}",
            "Cursor Usage",
            0x10,
        )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cursor usage float")
    parser.add_argument(
        "--settings",
        action="store_true",
        help="Abrir solo el diálogo de configuración",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()

    if args.settings:
        try:
            from .settings_standalone import run_settings_dialog

            run_settings_dialog()
        except Exception as exc:  # noqa: BLE001
            _report_fatal_error(exc, component="configuración")
            return 1
        return 0

    from .auth import resolve_session_token
    from .config import AppConfig
    from .float_app import FloatApp

    config = AppConfig.load()

    def get_token() -> tuple[str | None, str]:
        return resolve_session_token()

    try:
        FloatApp(config=config, get_token=get_token).run()
    except Exception as exc:  # noqa: BLE001
        _report_fatal_error(exc, component="flotante")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
