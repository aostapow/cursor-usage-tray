from __future__ import annotations

import ctypes
import subprocess
import sys
import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

from .__version__ import __version__
from .config import APP_DIR, CONFIG_PATH, AppConfig
from .modern_menu import _place_win32_topmost
from .startup import is_startup_enabled, set_startup_enabled
from .ui_theme import apply_theme, card, tk_check


def _parse_int(value: object) -> int:
    text = str(value).strip().replace(",", ".")
    if not text:
        raise ValueError("empty")
    return int(float(text))


def _parse_float(value: object) -> float:
    text = str(value).strip().replace(",", ".")
    if not text:
        raise ValueError("empty")
    return float(text)


def _win_alert(message: str, *, error: bool = False) -> None:
    if sys.platform != "win32":
        return
    flags = 0x10 if error else 0x40
    ctypes.windll.user32.MessageBoxW(None, message, "Cursor Usage", flags)


class SettingsDialog:
    def __init__(
        self,
        config: AppConfig,
        on_save: Callable[[AppConfig], None],
        parent: Optional[tk.Misc] = None,
        on_reset_label_position: Optional[Callable[[], None]] = None,
        on_get_label_position: Optional[Callable[[], tuple[int | None, int | None]]] = None,
        on_dialog_closed: Optional[Callable[[], None]] = None,
    ) -> None:
        self._config = config
        self._on_save = on_save
        self._on_reset_label_position = on_reset_label_position
        self._on_get_label_position = on_get_label_position
        self._on_dialog_closed = on_dialog_closed
        self._root = tk.Toplevel(parent) if parent else tk.Tk()
        if not parent:
            self._root.withdraw()
        self._root.title(f"Cursor Usage v{__version__}")
        self._root.resizable(False, False)
        apply_theme(self._root)
        self._build()
        self._root.protocol("WM_DELETE_WINDOW", self._close)
        if parent:
            self._root.transient(parent)
        self._root.grab_set()
        self._root.deiconify()
        self._root.update_idletasks()
        _place_win32_topmost(self._root, self._root.winfo_x(), self._root.winfo_y())
        self._root.focus_force()

    def _build(self) -> None:
        outer = ttk.Frame(self._root, padding=18)
        outer.grid(row=0, column=0, sticky="nsew")

        ttk.Label(outer, text="Cursor Usage", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            outer,
            text=f"Consumo on-demand en pantalla · v{__version__}",
            style="Muted.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(2, 14))

        panel = card(outer)
        panel.grid(row=2, column=0, sticky="ew")

        row = 0
        ttk.Label(panel, text="Refresco de datos", style="Card.TLabel", font=("Segoe UI Semibold", 11)).grid(
            row=row, column=0, columnspan=2, sticky="w"
        )
        row += 1
        ttk.Label(panel, text="Actualizar consumo cada (segundos)", style="CardMuted.TLabel").grid(
            row=row, column=0, sticky="w", pady=(10, 0)
        )
        self._refresh_var = tk.StringVar(value=str(self._config.refresh_interval_seconds))
        self._refresh_spin = ttk.Spinbox(
            panel, from_=60, to=3600, increment=30, textvariable=self._refresh_var, width=10
        )
        self._refresh_spin.grid(row=row, column=1, sticky="e", pady=(10, 0))
        row += 1

        ttk.Separator(panel).grid(row=row, column=0, columnspan=2, sticky="ew", pady=14)
        row += 1

        ttk.Label(panel, text="Alternancia del monto", style="Card.TLabel", font=("Segoe UI Semibold", 11)).grid(
            row=row, column=0, columnspan=2, sticky="w"
        )
        row += 1
        ttk.Label(panel, text="Alternar cada (segundos, 0 = desactivado)", style="CardMuted.TLabel").grid(
            row=row, column=0, sticky="w", pady=(10, 0)
        )
        self._alternate_var = tk.StringVar(value=str(self._config.label_alternate_seconds))
        self._alternate_spin = ttk.Spinbox(
            panel, from_=0, to=3600, increment=5, textvariable=self._alternate_var, width=10
        )
        self._alternate_spin.grid(row=row, column=1, sticky="e", pady=(10, 0))
        row += 1

        self._usd_var = tk.BooleanVar(value=self._config.label_show_usd)
        tk_check(panel, text="Mostrar USD on-demand", variable=self._usd_var).grid(
            row=row, column=0, columnspan=2, sticky="w", pady=(8, 0)
        )
        row += 1
        self._tokens_var = tk.BooleanVar(value=self._config.label_show_tokens)
        tk_check(panel, text="Mostrar tokens del ciclo", variable=self._tokens_var).grid(
            row=row, column=0, columnspan=2, sticky="w", pady=(4, 0)
        )
        row += 1
        self._plan_var = tk.BooleanVar(value=self._config.label_show_plan)
        tk_check(panel, text="Mostrar uso del plan", variable=self._plan_var).grid(
            row=row, column=0, columnspan=2, sticky="w", pady=(4, 0)
        )
        row += 1

        ttk.Separator(panel).grid(row=row, column=0, columnspan=2, sticky="ew", pady=14)
        row += 1

        ttk.Label(panel, text="Posición del monto", style="Card.TLabel", font=("Segoe UI Semibold", 11)).grid(
            row=row, column=0, columnspan=2, sticky="w"
        )
        row += 1
        ttk.Label(
            panel,
            text="Arrastrá el monto con el mouse para ubicarlo donde quieras.",
            style="CardMuted.TLabel",
            wraplength=380,
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(8, 0))
        row += 1
        ttk.Button(
            panel,
            text="Restablecer posición",
            style="Ghost.TButton",
            command=self._reset_label_position,
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(8, 0))
        row += 1

        self._dashboard_click_var = tk.BooleanVar(value=self._config.open_dashboard_on_click)
        tk_check(panel, text="Clic izquierdo abre el dashboard", variable=self._dashboard_click_var).grid(
            row=row, column=0, columnspan=2, sticky="w", pady=(8, 0)
        )
        row += 1

        ttk.Separator(panel).grid(row=row, column=0, columnspan=2, sticky="ew", pady=14)
        row += 1

        ttk.Label(panel, text="Umbrales de color (USD)", style="Card.TLabel", font=("Segoe UI Semibold", 11)).grid(
            row=row, column=0, columnspan=2, sticky="w"
        )
        row += 1
        ttk.Label(panel, text="Verde si es menor a", style="CardMuted.TLabel").grid(row=row, column=0, sticky="w", pady=(8, 0))
        self._green_var = tk.StringVar(value=str(self._config.threshold_green_max))
        self._green_spin = ttk.Spinbox(
            panel, from_=0, to=9999, increment=1, textvariable=self._green_var, width=10
        )
        self._green_spin.grid(row=row, column=1, sticky="e", pady=(8, 0))
        row += 1
        ttk.Label(panel, text="Amarillo hasta (inclusive)", style="CardMuted.TLabel").grid(
            row=row, column=0, sticky="w", pady=(6, 0)
        )
        self._yellow_var = tk.StringVar(value=str(self._config.threshold_yellow_max))
        self._yellow_spin = ttk.Spinbox(
            panel, from_=0, to=9999, increment=1, textvariable=self._yellow_var, width=10
        )
        self._yellow_spin.grid(row=row, column=1, sticky="e", pady=(6, 0))
        row += 1

        ttk.Separator(panel).grid(row=row, column=0, columnspan=2, sticky="ew", pady=14)
        row += 1

        self._startup_var = tk.BooleanVar(value=self._config.start_with_windows or is_startup_enabled())
        tk_check(panel, text="Iniciar con Windows", variable=self._startup_var).grid(
            row=row, column=0, columnspan=2, sticky="w"
        )
        row += 1

        self._auto_install_var = tk.BooleanVar(value=self._config.auto_install_updates)
        tk_check(
            panel,
            text="Instalar actualizaciones automáticamente (reinicia el flotante)",
            variable=self._auto_install_var,
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(8, 0))
        row += 1
        ttk.Label(
            panel,
            text="Las actualizaciones se gestionan desde el icono de la bandeja.",
            style="CardMuted.TLabel",
            wraplength=380,
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(4, 0))
        row += 1

        buttons = ttk.Frame(outer)
        buttons.grid(row=3, column=0, sticky="e", pady=(16, 0))
        ttk.Button(buttons, text="Abrir carpeta", style="Ghost.TButton", command=self._open_folder).grid(
            row=0, column=0, padx=(0, 8)
        )
        ttk.Button(buttons, text="Cancelar", style="Ghost.TButton", command=self._close).grid(row=0, column=1, padx=(0, 8))
        self._save_button = ttk.Button(buttons, text="Guardar", style="Accent.TButton", command=self._save)
        self._save_button.grid(row=0, column=2)

    def _reset_label_position(self) -> None:
        self._config.label_x = None
        self._config.label_y = None
        if self._on_reset_label_position:
            self._on_reset_label_position()

    def _open_folder(self) -> None:
        APP_DIR.mkdir(parents=True, exist_ok=True)
        if not CONFIG_PATH.exists():
            self._config.save()
        subprocess.Popen(["explorer", "/select,", str(CONFIG_PATH)])  # noqa: S603

    def _read_form_values(self) -> tuple[int, int, float, float]:
        try:
            self._save_button.focus_set()
        except tk.TclError:
            pass
        self._root.update_idletasks()
        refresh = max(60, _parse_int(self._refresh_spin.get()))
        alternate = max(0, _parse_int(self._alternate_var.get()))
        green_max = _parse_float(self._green_spin.get())
        yellow_max = _parse_float(self._yellow_spin.get())
        return refresh, alternate, green_max, yellow_max

    def _save(self) -> None:
        try:
            refresh, alternate, green_max, yellow_max = self._read_form_values()
        except (tk.TclError, ValueError, TypeError):
            _win_alert("Revisá los valores numéricos.", error=True)
            return

        if yellow_max < green_max:
            _win_alert("El umbral amarillo debe ser mayor o igual al umbral verde.", error=True)
            return

        show_usd = bool(self._usd_var.get())
        show_tokens = bool(self._tokens_var.get())
        show_plan = bool(self._plan_var.get())
        if not (show_usd or show_tokens or show_plan):
            _win_alert("Activá al menos un modo de visualización del monto.", error=True)
            return

        startup = bool(self._startup_var.get())
        label_x, label_y = self._config.label_x, self._config.label_y
        if self._on_get_label_position:
            label_x, label_y = self._on_get_label_position()

        updated = AppConfig(
            refresh_interval_seconds=refresh,
            display_mode=self._config.display_mode,
            open_dashboard_on_click=bool(self._dashboard_click_var.get()),
            show_taskbar_label=True,
            show_tray_icon=True,
            start_with_windows=startup,
            label_x=label_x,
            label_y=label_y,
            threshold_green_max=green_max,
            threshold_yellow_max=yellow_max,
            label_alternate_seconds=alternate,
            label_show_usd=show_usd,
            label_show_tokens=show_tokens,
            label_show_plan=show_plan,
            auto_install_updates=bool(self._auto_install_var.get()),
        )

        try:
            updated.save()
        except OSError as exc:
            _win_alert(f"No se pudo guardar la configuración.\n{exc}", error=True)
            return

        try:
            set_startup_enabled(startup)
        except OSError as exc:
            _win_alert(
                f"Configuración guardada, pero no se pudo actualizar el inicio con Windows.\n{exc}",
                error=True,
            )

        try:
            self._on_save(updated)
        except Exception as exc:  # noqa: BLE001
            _win_alert(f"Configuración guardada, pero hubo un error al aplicarla.\n{exc}", error=True)

        self._close()

    def _close(self) -> None:
        callback = self._on_dialog_closed
        self._on_dialog_closed = None
        try:
            self._root.attributes("-topmost", False)
        except tk.TclError:
            pass
        try:
            self._root.grab_release()
        except tk.TclError:
            pass
        try:
            self._root.destroy()
        except tk.TclError:
            pass
        if callback:
            callback()

    def show(self) -> None:
        self._root.deiconify()
        self._root.mainloop()


def open_settings_dialog(
    config: AppConfig,
    on_save: Callable[[AppConfig], None],
    parent: Optional[tk.Misc] = None,
    on_reset_label_position: Optional[Callable[[], None]] = None,
    on_get_label_position: Optional[Callable[[], tuple[int | None, int | None]]] = None,
    on_dialog_closed: Optional[Callable[[], None]] = None,
) -> None:
    if parent is not None:

        def _open() -> None:
            SettingsDialog(
                config,
                on_save,
                parent=parent,
                on_reset_label_position=on_reset_label_position,
                on_get_label_position=on_get_label_position,
                on_dialog_closed=on_dialog_closed,
            )

        parent.after(0, _open)
        return

    SettingsDialog(
        config,
        on_save,
        on_reset_label_position=on_reset_label_position,
        on_get_label_position=on_get_label_position,
        on_dialog_closed=on_dialog_closed,
    ).show()
