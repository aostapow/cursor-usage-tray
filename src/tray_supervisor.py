from __future__ import annotations

import ctypes
import subprocess
import sys
import threading
import time
import webbrowser
from typing import Optional

import pystray

from .__version__ import __version__
from .config import AppConfig
from .icons import make_tray_icon
from .installer import install_float_update
from .paths import ensure_app_dirs, float_launch_command, settings_launch_command
from .shutdown import create_shutdown_event, reset_shutdown_event, signal_shutdown
from .ipc_signals import signal_refresh
from .state_store import read_state
from .api import DASHBOARD_URL
from .updater import UpdateInfo, dismiss_version, fetch_latest_release, is_dismissed, is_newer

MB_YESNO = 0x04
MB_YESNOCANCEL = 0x03
MB_ICONQUESTION = 0x20
MB_ICONINFORMATION = 0x40
MB_ICONERROR = 0x10
IDYES = 6
IDNO = 7
IDCANCEL = 2


def _message_box(text: str, title: str = "Cursor Usage", flags: int = MB_ICONINFORMATION) -> int:
    return int(ctypes.windll.user32.MessageBoxW(None, text, title, flags))


class TraySupervisor:
    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._stop = threading.Event()
        self._float_process: subprocess.Popen | None = None
        self._float_lock = threading.Lock()
        self._intentional_float_stop = False
        self._shutdown_event = create_shutdown_event()
        self._settings_process: subprocess.Popen | None = None
        self._icon = pystray.Icon(
            "cursor-usage-tray",
            make_tray_icon(),
            "Cursor usage",
            menu=pystray.Menu(
                pystray.MenuItem("Actualizar ahora", self._menu_refresh),
                pystray.MenuItem("Abrir dashboard", self._menu_open_dashboard),
                pystray.MenuItem("Configuración", self._menu_settings),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Reiniciar flotante", self._menu_restart_float),
                pystray.MenuItem("Buscar actualizaciones", self._menu_check_updates),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Salir", self._menu_quit),
            ),
        )

    def _apply_state_to_icon(self) -> None:
        state = read_state()
        thresholds = self._config.usage_thresholds()
        try:
            if state and state.has_error:
                self._icon.icon = make_tray_icon(error=True)
                self._icon.title = state.tray_tip
            elif state and state.on_demand_usd is not None:
                self._icon.icon = make_tray_icon(state.on_demand_usd, thresholds=thresholds)
                self._icon.title = state.tray_tip
            else:
                self._icon.icon = make_tray_icon(thresholds=thresholds)
                self._icon.title = state.tray_tip if state else "Cursor usage"
        except (ValueError, OSError):
            pass

    def _state_poll_loop(self) -> None:
        while not self._stop.wait(5):
            self._config = AppConfig.load()
            self._apply_state_to_icon()

    def _spawn_float(self) -> None:
        with self._float_lock:
            if self._float_process and self._float_process.poll() is None:
                return
            reset_shutdown_event()
            cmd = float_launch_command()
            self._float_process = subprocess.Popen(cmd)  # noqa: S603
            self._intentional_float_stop = False

    def _stop_float(self, *, graceful: bool = True, timeout: float = 8.0) -> None:
        with self._float_lock:
            proc = self._float_process
            if proc is None or proc.poll() is not None:
                self._float_process = None
                return
            self._intentional_float_stop = True
            if graceful:
                signal_shutdown()
            try:
                proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=3)
            self._float_process = None

    def _watch_float_loop(self) -> None:
        while not self._stop.wait(2):
            with self._float_lock:
                proc = self._float_process
                intentional = self._intentional_float_stop
            if proc is None:
                continue
            code = proc.poll()
            if code is None:
                continue
            with self._float_lock:
                self._float_process = None
            if self._stop.is_set() or intentional:
                continue
            if code != 0:
                time.sleep(1)
                if not self._stop.is_set():
                    self._spawn_float()

    def _menu_restart_float(self, _icon: pystray.Icon, _item: pystray.MenuItem) -> None:
        self._stop_float(graceful=True)
        self._spawn_float()

    def _menu_refresh(self, _icon: pystray.Icon, _item: pystray.MenuItem) -> None:
        signal_refresh()

    def _menu_open_dashboard(self, _icon: pystray.Icon, _item: pystray.MenuItem) -> None:
        webbrowser.open(DASHBOARD_URL)

    def _menu_settings(self, _icon: pystray.Icon, _item: pystray.MenuItem) -> None:
        if self._settings_process and self._settings_process.poll() is None:
            return
        cmd = settings_launch_command()
        self._settings_process = subprocess.Popen(cmd)  # noqa: S603

    def _menu_quit(self, _icon: pystray.Icon, _item: pystray.MenuItem) -> None:
        self._request_quit()

    def _request_quit(self) -> None:
        self._stop.set()
        try:
            self._icon.stop()
        except Exception:  # noqa: BLE001
            pass

    def _shutdown(self) -> None:
        self._stop.set()
        self._stop_float(graceful=True, timeout=5.0)

    def _prompt_manual_update(self, info: UpdateInfo) -> None:
        result = _message_box(
            (
                f"Hay una versión nueva: v{info.version}\n"
                f"Tenés instalada la v{__version__}.\n\n"
                "¿Abrir la página de descarga?"
            ),
            flags=MB_YESNOCANCEL | MB_ICONQUESTION,
        )
        if result == IDYES:
            webbrowser.open(info.download_url or info.page_url)
        elif result == IDNO:
            dismiss_version(info.version)

    def _prompt_auto_install(self, info: UpdateInfo) -> None:
        result = _message_box(
            (
                f"Hay una versión nueva: v{info.version}\n"
                f"Tenés instalada la v{__version__}.\n\n"
                "¿Instalar ahora? Se cerrará el monto flotante y se reiniciará automáticamente."
            ),
            flags=MB_YESNO | MB_ICONQUESTION,
        )
        if result != IDYES:
            return

        def work() -> None:
            try:
                self._stop_float(graceful=True)
                install_float_update(info)
                self._spawn_float()
                _message_box(
                    f"Actualización v{info.version} instalada.\nEl monto flotante fue reiniciado.",
                )
            except Exception as exc:  # noqa: BLE001
                _message_box(f"No se pudo instalar la actualización.\n{exc}", flags=MB_ICONERROR)
                self._spawn_float()

        threading.Thread(target=work, daemon=True).start()

    def _handle_update_info(self, info: UpdateInfo, *, notify_if_current: bool) -> None:
        if is_newer(info.version):
            if self._config.auto_install_updates and info.download_url:
                self._prompt_auto_install(info)
            elif not is_dismissed(info.version):
                self._prompt_manual_update(info)
        elif notify_if_current:
            _message_box(f"Tenés la última versión (v{__version__}).")

    def _check_updates(self, *, notify_if_current: bool) -> None:
        def work() -> None:
            try:
                info = fetch_latest_release()
            except Exception as exc:  # noqa: BLE001
                _message_box(f"No se pudo buscar actualizaciones.\n{exc}", flags=MB_ICONERROR)
                return
            if not info:
                if notify_if_current:
                    _message_box(f"Tenés la última versión (v{__version__}).")
                return
            self._handle_update_info(info, notify_if_current=notify_if_current)

        threading.Thread(target=work, daemon=True).start()

    def _check_updates_on_startup(self) -> None:
        def work() -> None:
            try:
                info = fetch_latest_release()
            except Exception:
                return
            if not info or not is_newer(info.version):
                return
            if not self._config.auto_install_updates and is_dismissed(info.version):
                return
            self._handle_update_info(info, notify_if_current=False)

        threading.Thread(target=work, daemon=True).start()

    def _menu_check_updates(self, _icon: pystray.Icon, _item: pystray.MenuItem) -> None:
        self._check_updates(notify_if_current=True)

    def run(self) -> None:
        ensure_app_dirs()
        self._spawn_float()
        threading.Thread(target=self._state_poll_loop, daemon=True).start()
        threading.Thread(target=self._watch_float_loop, daemon=True).start()
        self._check_updates_on_startup()
        self._apply_state_to_icon()
        self._icon.run()
        self._shutdown()
