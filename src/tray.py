from __future__ import annotations

import threading
import tkinter as tk
import webbrowser
from tkinter import messagebox
from typing import Callable, Optional

import pystray

from .__version__ import __version__
from .api import CursorUsageClient, DASHBOARD_URL, UsageSnapshot
from .config import AppConfig
from .icons import make_tray_icon
from .modern_menu import MenuAction, ModernPopupMenu, pointer_xy
from .settings import open_settings_dialog
from .label_modes import current_display
from .taskbar_label import TaskbarLabel
from .usage_basis import usage_percent
from .updater import (
    UpdateInfo,
    dismiss_version,
    fetch_latest_release,
    is_dismissed,
    is_newer,
)

TRAY_TIP_MAX = 127


def _tray_tip(text: str) -> str:
    compact = " ".join(text.replace("\r\n", "\n").split())
    if len(compact) <= TRAY_TIP_MAX:
        return compact
    return compact[: TRAY_TIP_MAX - 1] + "…"


def _snapshot_tray_tip(snapshot: UsageSnapshot) -> str:
    plan = snapshot.membership_type or "unknown"
    return f"Cursor on-demand ${snapshot.on_demand_usd:.2f} · {plan}"


class UsageTrayApp:
    def __init__(
        self,
        config: AppConfig,
        get_token: Callable[[], tuple[Optional[str], str]],
    ) -> None:
        self._config = config
        self._get_token = get_token
        self._refresh_seconds = max(60, config.refresh_interval_seconds)
        self._show_taskbar_label = config.show_taskbar_label
        self._snapshot: Optional[UsageSnapshot] = None
        self._last_error: Optional[str] = None
        self._token_source: str = ""
        self._stop = threading.Event()
        self._taskbar: Optional[TaskbarLabel] = None
        self._tk_root: Optional[tk.Tk] = None
        self._popup_menu: Optional[ModernPopupMenu] = None
        self._icon = pystray.Icon(
            "cursor-usage-tray",
            make_tray_icon(),
            "Cursor usage",
            menu=pystray.Menu(
                pystray.MenuItem("Actualizar", self._menu_refresh),
                pystray.MenuItem("Dashboard", self._menu_open_dashboard),
                pystray.MenuItem("Configuración", self._menu_settings),
                pystray.MenuItem("Buscar actualizaciones", self._menu_check_updates),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Salir", self._menu_quit),
            ),
        )

    def _on_config_saved(self, config: AppConfig) -> None:
        self._config = config
        self._refresh_seconds = max(60, config.refresh_interval_seconds)
        self._show_taskbar_label = config.show_taskbar_label
        self._icon.default_action = None
        if self._taskbar:
            self._taskbar.set_visible(config.show_taskbar_label)
            self._taskbar.set_thresholds(config.usage_thresholds())
            self._taskbar.set_appearance(
                config.label_bg_color,
                config.resolved_label_fg(),
                config.threshold_colors(),
            )
            if config.label_x is not None and config.label_y is not None:
                self._taskbar.apply_saved_position(config.label_x, config.label_y)
            self._taskbar.set_left_click_handler(None)
            self._taskbar.set_double_click_handler(self._open_dashboard)
        self._apply_ui()

    def _get_label_position(self) -> tuple[int | None, int | None]:
        if not self._taskbar:
            return self._config.label_x, self._config.label_y
        x, y = self._taskbar.current_position()
        return x, y

    def _on_label_position_changed(self, x: int, y: int) -> None:
        self._config.label_x = x
        self._config.label_y = y
        self._config.save()

    def _reset_label_position(self) -> None:
        if self._taskbar:
            self._taskbar.reset_position()

    def _open_settings_from_label(self) -> None:
        parent = self._taskbar.root if self._taskbar else self._tk_root
        if not parent:
            return
        self._pause_label_front()
        open_settings_dialog(
            self._config,
            self._on_config_saved,
            parent=parent,
            on_reset_label_position=self._reset_label_position,
            on_get_label_position=self._get_label_position,
            on_dialog_closed=self._resume_label_front,
        )

    def _pause_label_front(self) -> None:
        if self._taskbar:
            self._taskbar.pause_front()

    def _resume_label_front(self) -> None:
        if self._taskbar:
            self._taskbar.resume_front()

    def _menu_refresh(self, _icon: pystray.Icon, _item: pystray.MenuItem) -> None:
        self.refresh_once()

    def _open_dashboard(self) -> None:
        webbrowser.open(DASHBOARD_URL)

    def _menu_open_dashboard(self, _icon: pystray.Icon, _item: pystray.MenuItem) -> None:
        self._open_dashboard()

    def _menu_settings(self, _icon: pystray.Icon, _item: pystray.MenuItem) -> None:
        parent = self._taskbar.root if self._taskbar else self._tk_root
        if parent:
            self._pause_label_front()
            open_settings_dialog(
                self._config,
                self._on_config_saved,
                parent=parent,
                on_reset_label_position=self._reset_label_position,
                on_get_label_position=self._get_label_position,
                on_dialog_closed=self._resume_label_front,
            )

    def _quit(self) -> None:
        self._stop.set()
        if self._popup_menu:
            self._popup_menu.close()
        if self._taskbar:
            self._taskbar.close()
        self._icon.stop()

    def _menu_quit(self, _icon: pystray.Icon, _item: pystray.MenuItem) -> None:
        self._quit()

    def _tk_parent(self) -> tk.Misc | None:
        if self._taskbar:
            return self._taskbar.root
        return self._tk_root

    def _prompt_update(self, info: UpdateInfo) -> None:
        parent = self._tk_parent()
        result = messagebox.askyesnocancel(
            "Actualización disponible",
            (
                f"Hay una versión nueva: {info.version}\n"
                f"Tenés instalada la {__version__}.\n\n"
                "¿Abrir la página de descarga?"
            ),
            parent=parent,
        )
        if result is True:
            webbrowser.open(info.download_url or info.page_url)
        elif result is False:
            dismiss_version(info.version)

    def _show_up_to_date(self) -> None:
        parent = self._tk_parent()
        messagebox.showinfo(
            "Cursor Usage",
            f"Tenés la última versión ({__version__}).",
            parent=parent,
        )

    def _show_update_error(self, error: str) -> None:
        parent = self._tk_parent()
        messagebox.showerror(
            "Cursor Usage",
            f"No se pudo buscar actualizaciones.\n{error}",
            parent=parent,
        )

    def _check_updates(self, *, notify_if_current: bool) -> None:
        def work() -> None:
            try:
                info = fetch_latest_release()
            except Exception as exc:  # noqa: BLE001
                root = self._tk_parent()
                if root:
                    root.after(0, lambda: self._show_update_error(str(exc)))
                return

            root = self._tk_parent()
            if not root:
                return

            if info and is_newer(info.version):
                root.after(0, lambda: self._prompt_update(info))
            elif notify_if_current:
                root.after(0, self._show_up_to_date)

        threading.Thread(target=work, daemon=True).start()

    def _check_updates_on_startup(self) -> None:
        def work() -> None:
            try:
                info = fetch_latest_release()
            except Exception:
                return
            if not info or not is_newer(info.version) or is_dismissed(info.version):
                return
            root = self._tk_parent()
            if root:
                root.after(0, lambda: self._prompt_update(info))

        threading.Thread(target=work, daemon=True).start()

    def _menu_check_updates(self, _icon: pystray.Icon, _item: pystray.MenuItem) -> None:
        self._check_updates(notify_if_current=True)

    def _show_context_menu(self, event: tk.Event) -> None:
        parent = self._taskbar.root if self._taskbar else self._tk_root
        if not parent or not self._popup_menu:
            return
        self._pause_label_front()
        menu_x, menu_y = pointer_xy(int(event.x_root), int(event.y_root))
        self._popup_menu.show(
            menu_x,
            menu_y,
            [
                MenuAction("Actualizar ahora", self.refresh_once),
                MenuAction("Abrir dashboard", self._open_dashboard),
                MenuAction(
                    "Configuración",
                    self._open_settings_from_label,
                ),
                MenuAction("Buscar actualizaciones", lambda: self._check_updates(notify_if_current=True)),
                MenuAction("---", lambda: None),
                MenuAction("Salir", self._quit, destructive=True),
            ],
            on_closed=self._resume_label_front,
        )

    def _apply_ui(self) -> None:
        threshold_amount: float | None = None
        taskbar_text = "$-.--"
        tooltip = "Cursor usage"
        tray_tip = "Cursor usage"
        has_error = False

        if self._snapshot:
            display = current_display(self._config, self._snapshot, mode_index=0, error=False)
            threshold_amount = display.usage_percent if display.use_threshold_colors else usage_percent(
                self._snapshot, self._config.usage_basis_enum()
            )
            taskbar_text = display.text
            tooltip = self._snapshot.tooltip
            tray_tip = _tray_tip(_snapshot_tray_tip(self._snapshot))
        elif self._last_error:
            taskbar_text = "$!"
            tooltip = self._last_error
            tray_tip = _tray_tip(self._last_error)
            has_error = True
        else:
            taskbar_text = "$?"
            tooltip = "Sin datos de consumo"
            tray_tip = "Sin datos de consumo"

        if self._taskbar:

            thresholds = self._config.usage_thresholds()
            fg_override = None if threshold_amount is not None else self._config.resolved_label_fg()

            def update_taskbar() -> None:
                self._taskbar.update(
                    taskbar_text,
                    usage_percent=threshold_amount,
                    tooltip=tooltip,
                    thresholds=thresholds,
                    fg_override=fg_override,
                )

            try:
                self._taskbar.root.after(0, update_taskbar)
            except tk.TclError:
                pass

        thresholds = self._config.usage_thresholds()
        colors = self._config.threshold_colors()
        try:
            if has_error:
                self._icon.icon = make_tray_icon(error=True, colors=colors)
            elif self._snapshot:
                icon_pct = usage_percent(self._snapshot, self._config.usage_basis_enum())
                self._icon.icon = make_tray_icon(icon_pct, thresholds=thresholds, colors=colors)
            else:
                self._icon.icon = make_tray_icon(thresholds=thresholds, colors=colors)
            self._icon.title = tray_tip
        except (ValueError, OSError):
            pass

    def refresh_once(self) -> None:
        token, source = self._get_token()
        self._token_source = source if token else ""
        if not token:
            self._snapshot = None
            self._last_error = (
                f"Sin sesión de Cursor.\n{source}\n"
                "Abrí Cursor, iniciá sesión y volvé a actualizar."
            )
            self._apply_ui()
            return

        try:
            client = CursorUsageClient(token)
            self._snapshot = client.fetch_usage_summary()
            self._last_error = None
        except PermissionError as exc:
            self._snapshot = None
            self._last_error = str(exc)
        except Exception as exc:  # noqa: BLE001
            self._snapshot = None
            self._last_error = f"Error al consultar uso: {exc}"
        self._apply_ui()

    def _loop(self) -> None:
        while not self._stop.wait(self._refresh_seconds):
            self.refresh_once()

    def run(self) -> None:
        threading.Thread(target=self._icon.run, daemon=True).start()

        if self._show_taskbar_label:
            self._taskbar = TaskbarLabel(
                initial_x=self._config.label_x,
                initial_y=self._config.label_y,
                thresholds=self._config.usage_thresholds(),
                bg_color=self._config.label_bg_color,
                base_fg=self._config.resolved_label_fg(),
                threshold_colors=self._config.threshold_colors(),
                on_position_changed=self._on_label_position_changed,
                on_double_click=self._open_dashboard,
                on_right_click=self._show_context_menu,
            )
            self._tk_root = self._taskbar.root
        else:
            self._tk_root = tk.Tk()
            self._tk_root.withdraw()

        self._popup_menu = ModernPopupMenu(self._tk_root)
        self.refresh_once()
        threading.Thread(target=self._loop, daemon=True).start()
        self._check_updates_on_startup()

        if self._show_taskbar_label:
            self._taskbar.run()
            return

        self._tk_root.mainloop()
