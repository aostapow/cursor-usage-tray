from __future__ import annotations

import threading
import webbrowser
from typing import Callable, Optional

from .api import CursorUsageClient, DASHBOARD_URL, UsageSnapshot
from .config import AppConfig
from .ipc_signals import config_mtime, consume_label_reset_request, wait_refresh
from .label_modes import current_display, enabled_modes
from .shutdown import close_handle, open_shutdown_event, wait_shutdown
from .state_store import AppState, write_state
from .taskbar_label import TaskbarLabel
from .usage_levels import usage_style
from .__version__ import __version__

TRAY_TIP_MAX = 127


def _tray_tip(text: str) -> str:
    compact = " ".join(text.replace("\r\n", "\n").split())
    if len(compact) <= TRAY_TIP_MAX:
        return compact
    return compact[: TRAY_TIP_MAX - 1] + "…"


def _snapshot_tray_tip(snapshot: UsageSnapshot) -> str:
    plan = snapshot.membership_type or "unknown"
    return f"Cursor on-demand ${snapshot.on_demand_usd:.2f} · {plan}"


class FloatApp:
    def __init__(
        self,
        config: AppConfig,
        get_token: Callable[[], tuple[Optional[str], str]],
    ) -> None:
        self._config = config
        self._get_token = get_token
        self._refresh_seconds = max(60, config.refresh_interval_seconds)
        self._open_dashboard_on_click = config.open_dashboard_on_click
        self._snapshot: Optional[UsageSnapshot] = None
        self._last_error: Optional[str] = None
        self._stop = threading.Event()
        self._taskbar: Optional[TaskbarLabel] = None
        self._label_mode_index = 0
        self._alternate_job: str | None = None
        self._shutdown_handle = open_shutdown_event()
        self._external_watch_stop = threading.Event()
        self._refresh_in_flight = threading.Event()
        self._config_mtime = config_mtime()

    def _main_thread(self) -> bool:
        return threading.current_thread() is threading.main_thread()

    def _run_on_main(self, callback: Callable[[], None]) -> None:
        if not self._taskbar:
            callback()
            return
        if self._main_thread():
            callback()
        else:
            self._taskbar.root.after(0, callback)

    def _needs_tokens(self) -> bool:
        return self._config.label_show_tokens

    def _on_config_saved(self, config: AppConfig) -> None:
        self._config = config
        self._refresh_seconds = max(60, config.refresh_interval_seconds)
        self._open_dashboard_on_click = config.open_dashboard_on_click
        self._label_mode_index = 0
        if self._taskbar:
            self._taskbar.set_thresholds(config.usage_thresholds())
            if config.label_x is not None and config.label_y is not None:
                cx, cy = self._taskbar.current_position()
                if config.label_x != cx or config.label_y != cy:
                    self._taskbar.apply_saved_position(config.label_x, config.label_y)
            self._taskbar.set_left_click_handler(
                self._open_dashboard if config.open_dashboard_on_click else None
            )
        self._run_on_main(self._restart_alternate_timer)
        self._apply_ui()

    def _on_label_position_changed(self, x: int, y: int) -> None:
        self._config.label_x = x
        self._config.label_y = y
        self._config.save()
        self._config_mtime = config_mtime()

    def _reset_label_position(self) -> None:
        if self._taskbar:
            self._taskbar.reset_position()

    def _open_dashboard(self) -> None:
        webbrowser.open(DASHBOARD_URL)

    def _quit(self) -> None:
        self._stop.set()
        self._external_watch_stop.set()
        self._cancel_alternate_timer()
        if self._taskbar:
            self._taskbar.close()
        close_handle(self._shutdown_handle)

    def _request_shutdown(self) -> None:
        if self._taskbar:
            self._taskbar.root.after(0, self._quit_and_exit)

    def _quit_and_exit(self) -> None:
        self._quit()
        if self._taskbar:
            try:
                self._taskbar.root.update_idletasks()
                self._taskbar.root.quit()
            except Exception:  # noqa: BLE001
                pass
        import sys

        sys.exit(0)

    def _write_shared_state(self, *, tray_tip: str, tooltip: str, has_error: bool) -> None:
        amount = self._snapshot.on_demand_usd if self._snapshot else None
        membership = self._snapshot.membership_type if self._snapshot else ""
        write_state(
            AppState(
                on_demand_usd=amount,
                membership_type=membership,
                tray_tip=tray_tip,
                tooltip=tooltip,
                has_error=has_error,
                float_version=__version__,
            )
        )

    def _apply_ui(self) -> None:
        has_error = bool(self._last_error)
        tooltip = "Cursor usage"
        tray_tip = "Cursor usage"

        if self._snapshot:
            tooltip = self._snapshot.tooltip
            tray_tip = _tray_tip(_snapshot_tray_tip(self._snapshot))
        elif self._last_error:
            tooltip = self._last_error
            tray_tip = _tray_tip(self._last_error)
        else:
            tooltip = "Sin datos de consumo"
            tray_tip = "Sin datos de consumo"

        self._write_shared_state(tray_tip=tray_tip, tooltip=tooltip, has_error=has_error)

        if not self._taskbar:
            return

        mode_index = self._label_mode_index if self._should_alternate() else 0
        display = current_display(
            self._config,
            self._snapshot,
            mode_index=mode_index,
            error=has_error,
        )
        thresholds = self._config.usage_thresholds()
        amount = display.amount_usd if display.use_threshold_colors else None
        if not display.use_threshold_colors:
            neutral = usage_style(None, thresholds)
            fg = neutral.fg
        else:
            fg = usage_style(amount, thresholds).fg

        def update_taskbar() -> None:
            self._taskbar.update(
                display.text,
                amount_usd=amount,
                tooltip=tooltip,
                thresholds=thresholds,
                fg_override=fg if not display.use_threshold_colors else None,
            )

        self._run_on_main(update_taskbar)

    def _should_alternate(self) -> bool:
        if self._config.label_alternate_seconds <= 0:
            return False
        return len(enabled_modes(self._config, self._snapshot)) > 1

    def _alternate_interval_ms(self) -> int:
        seconds = self._config.label_alternate_seconds
        if seconds <= 0:
            return 0
        return seconds * 1000

    def _cancel_alternate_timer(self) -> None:
        if not self._taskbar or not self._alternate_job:
            return
        try:
            self._taskbar.root.after_cancel(self._alternate_job)
        except Exception:  # noqa: BLE001
            pass
        self._alternate_job = None

    def _restart_alternate_timer(self) -> None:
        if not self._taskbar:
            return
        self._cancel_alternate_timer()
        self._label_mode_index = 0

        if not self._should_alternate():
            return

        interval_ms = self._alternate_interval_ms()

        def tick() -> None:
            if self._stop.is_set() or not self._taskbar:
                return
            self._alternate_job = None
            if not self._should_alternate():
                self._label_mode_index = 0
                return
            modes_now = enabled_modes(self._config, self._snapshot)
            self._label_mode_index = (self._label_mode_index + 1) % len(modes_now)
            self._apply_ui()
            next_ms = self._alternate_interval_ms()
            if next_ms > 0:
                self._alternate_job = self._taskbar.root.after(next_ms, tick)

        self._alternate_job = self._taskbar.root.after(interval_ms, tick)

    def _apply_refresh_result(
        self,
        *,
        snapshot: Optional[UsageSnapshot],
        error: Optional[str],
    ) -> None:
        self._snapshot = snapshot
        self._last_error = error
        self._label_mode_index = 0
        self._restart_alternate_timer()
        self._apply_ui()

    def _fetch_usage(self) -> tuple[Optional[UsageSnapshot], Optional[str]]:
        token, source = self._get_token()
        include_tokens = self._needs_tokens()
        if not token:
            return None, (
                f"Sin sesión de Cursor.\n{source}\n"
                "Abrí Cursor, iniciá sesión y volvé a actualizar."
            )

        try:
            client = CursorUsageClient(token)
            snapshot = client.fetch_snapshot_with_tokens(include_tokens=include_tokens)
            return snapshot, None
        except PermissionError as exc:
            return None, str(exc)
        except Exception as exc:  # noqa: BLE001
            return None, f"Error al consultar uso: {exc}"

    def refresh_once(self) -> None:
        if self._refresh_in_flight.is_set():
            return

        def work() -> None:
            if self._refresh_in_flight.is_set():
                return
            self._refresh_in_flight.set()
            try:
                snapshot, error = self._fetch_usage()
            finally:
                self._refresh_in_flight.clear()

            def apply() -> None:
                self._apply_refresh_result(snapshot=snapshot, error=error)

            self._run_on_main(apply)

        if self._main_thread():
            threading.Thread(target=work, daemon=True).start()
        else:
            work()

    def _loop(self) -> None:
        while not self._stop.wait(self._refresh_seconds):
            self.refresh_once()

    def _watch_external_signals(self) -> None:
        while not self._external_watch_stop.wait(0.5):
            if wait_shutdown(500):
                self._request_shutdown()
                break
            if wait_refresh(100):
                self.refresh_once()
            if consume_label_reset_request():
                self._run_on_main(self._reset_label_position)
            current_mtime = config_mtime()
            if current_mtime and current_mtime != self._config_mtime:
                self._config_mtime = current_mtime
                self._run_on_main(lambda: self._on_config_saved(AppConfig.load()))

    def run(self) -> None:
        self._taskbar = TaskbarLabel(
            initial_x=self._config.label_x,
            initial_y=self._config.label_y,
            thresholds=self._config.usage_thresholds(),
            on_position_changed=self._on_label_position_changed,
            on_left_click=self._open_dashboard if self._open_dashboard_on_click else None,
        )
        threading.Thread(target=self._watch_external_signals, daemon=True).start()
        self.refresh_once()
        threading.Thread(target=self._loop, daemon=True).start()
        self._taskbar.run()
