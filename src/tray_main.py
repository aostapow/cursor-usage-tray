from __future__ import annotations

import sys


def _report_fatal_error(exc: BaseException) -> None:
    from .config import APP_DIR

    APP_DIR.mkdir(parents=True, exist_ok=True)
    log_path = APP_DIR / "tray.log"
    log_path.write_text(f"{type(exc).__name__}: {exc}\n", encoding="utf-8")
    if sys.platform == "win32":
        import ctypes

        ctypes.windll.user32.MessageBoxW(
            None,
            f"No se pudo iniciar Cursor Usage (tray).\n\n{type(exc).__name__}: {exc}\n\nLog: {log_path}",
            "Cursor Usage",
            0x10,
        )


def main() -> int:
    from .config import AppConfig
    from .single_instance import exit_if_already_running
    from .startup import sync_startup_with_config
    from .tray_supervisor import TraySupervisor

    exit_if_already_running()

    config = AppConfig.load()
    sync_startup_with_config(config.start_with_windows)

    try:
        TraySupervisor(config=config).run()
    except Exception as exc:  # noqa: BLE001
        _report_fatal_error(exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
