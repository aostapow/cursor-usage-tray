from __future__ import annotations

import ctypes
import subprocess
import sys
import tkinter as tk
from tkinter import colorchooser, ttk
from typing import Callable, Optional

from .__version__ import __version__
from .config import APP_DIR, CONFIG_PATH, AppConfig
from .startup import is_startup_enabled, set_startup_enabled
from .taskbar_label import default_label_bg
from .ui_theme import CARD, apply_theme, card, color_swatch, compact_button, tk_check, tk_option
from .usage_basis import UsageBasis
from .usage_levels import (
    DEFAULT_LABEL_FG,
    DEFAULT_THRESHOLD_COLOR_HIGH,
    DEFAULT_THRESHOLD_COLOR_LOW,
    DEFAULT_THRESHOLD_COLOR_MEDIUM,
    HEX_COLOR_RE,
)


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
        panel.columnconfigure(1, weight=1)

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

        display_row = tk.Frame(panel, bg=CARD)
        display_row.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        display_row.columnconfigure(1, weight=1)
        self._usd_var = tk.BooleanVar(value=self._config.label_show_usd)
        tk_check(display_row, text="Mostrar USD", variable=self._usd_var).grid(row=0, column=0, sticky="w")
        self._plan_var = tk.BooleanVar(value=self._config.label_show_plan)
        tk_check(display_row, text="Mostrar uso del plan", variable=self._plan_var).grid(
            row=0, column=1, sticky="e"
        )
        row += 1
        tokens_row = tk.Frame(panel, bg=CARD)
        tokens_row.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(4, 0))
        tokens_row.columnconfigure(1, weight=1)
        self._tokens_var = tk.BooleanVar(value=self._config.label_show_tokens)
        tk_check(tokens_row, text="Mostrar tokens ciclo", variable=self._tokens_var).grid(
            row=0, column=0, sticky="w"
        )
        self._daily_tokens_var = tk.BooleanVar(value=self._config.label_show_daily_tokens)
        tk_check(tokens_row, text="Mostrar tokens diarios", variable=self._daily_tokens_var).grid(
            row=0, column=1, sticky="e"
        )
        row += 1

        ttk.Label(
            panel,
            text="Consumo para monto y umbrales",
            style="Card.TLabel",
            font=("Segoe UI Semibold", 11),
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(10, 0))
        row += 1
        self._usage_basis_var = tk.StringVar(value=UsageBasis.parse(self._config.usage_basis).value)
        basis_row = tk.Frame(panel, bg=CARD)
        basis_row.grid(row=row, column=0, columnspan=2, sticky="w", pady=(6, 0))
        tk_option(
            basis_row,
            text="Included usage",
            variable=self._usage_basis_var,
            value=UsageBasis.INCLUDED.value,
        ).pack(side="left", padx=(0, 12))
        tk_option(
            basis_row,
            text="On-demand",
            variable=self._usage_basis_var,
            value=UsageBasis.ON_DEMAND.value,
        ).pack(side="left", padx=(0, 12))
        tk_option(
            basis_row,
            text="Auto",
            variable=self._usage_basis_var,
            value=UsageBasis.AUTO.value,
        ).pack(side="left")
        row += 1

        ttk.Separator(panel).grid(row=row, column=0, columnspan=2, sticky="ew", pady=14)
        row += 1

        ttk.Label(panel, text="Apariencia del panel", style="Card.TLabel", font=("Segoe UI Semibold", 11)).grid(
            row=row, column=0, columnspan=2, sticky="w"
        )
        row += 1
        self._bg_color_var = tk.StringVar(value=self._config.label_bg_color or "")
        row = self._add_color_row(
            panel,
            row,
            "Color de fondo",
            self._bg_color_var,
            default_label_bg(),
        )
        self._fg_color_var = tk.StringVar(value=self._config.label_fg_color or "")
        row = self._add_color_row(
            panel,
            row,
            "Color de texto",
            self._fg_color_var,
            DEFAULT_LABEL_FG,
        )

        self._green_var = tk.StringVar(value=str(self._config.threshold_green_max))
        self._thresh_low_var = tk.StringVar(value=self._config.threshold_color_low)
        row = self._add_threshold_row(
            panel,
            row,
            "Umbral 1",
            self._thresh_low_var,
            DEFAULT_THRESHOLD_COLOR_LOW,
            self._green_var,
        )
        self._yellow_var = tk.StringVar(value=str(self._config.threshold_yellow_max))
        self._thresh_medium_var = tk.StringVar(value=self._config.threshold_color_medium)
        row = self._add_threshold_row(
            panel,
            row,
            "Umbral 2",
            self._thresh_medium_var,
            DEFAULT_THRESHOLD_COLOR_MEDIUM,
            self._yellow_var,
        )
        self._thresh_high_var = tk.StringVar(value=self._config.threshold_color_high)
        row = self._add_threshold_row(
            panel,
            row,
            "Umbral 3",
            self._thresh_high_var,
            DEFAULT_THRESHOLD_COLOR_HIGH,
        )

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

    def _add_color_row(
        self,
        panel: ttk.Frame,
        row: int,
        label_text: str,
        var: tk.StringVar,
        default: str,
    ) -> int:
        ttk.Label(panel, text=label_text, style="CardMuted.TLabel").grid(
            row=row, column=0, sticky="w", pady=(4, 0)
        )
        controls = tk.Frame(panel, bg=CARD)
        controls.grid(row=row, column=1, sticky="e", pady=(4, 0))
        preview_bg = var.get() or default

        def pick() -> None:
            initial = var.get() or default
            result = colorchooser.askcolor(color=initial, parent=self._root, title=label_text)
            if result and result[1]:
                var.set(result[1])
                swatch.set_color(result[1])

        swatch = color_swatch(controls, preview_bg, pick, parent_bg=CARD)
        swatch.pack(side="left", padx=(0, 4))
        compact_button(controls, "…", pick, width=22, parent_bg=CARD).pack(side="left")
        return row + 1

    def _add_threshold_row(
        self,
        panel: ttk.Frame,
        row: int,
        label_text: str,
        color_var: tk.StringVar,
        color_default: str,
        amount_var: tk.StringVar | None = None,
    ) -> int:
        ttk.Label(panel, text=label_text, style="CardMuted.TLabel").grid(
            row=row, column=0, sticky="w", pady=(6, 0)
        )
        controls = tk.Frame(panel, bg=CARD)
        controls.grid(row=row, column=1, sticky="e", pady=(6, 0))
        preview_bg = color_var.get() or color_default
        picker_title = f"{label_text} — color"

        def pick() -> None:
            initial = color_var.get() or color_default
            result = colorchooser.askcolor(color=initial, parent=self._root, title=picker_title)
            if result and result[1]:
                color_var.set(result[1])
                swatch.set_color(result[1])

        swatch = color_swatch(controls, preview_bg, pick, parent_bg=CARD)
        swatch.pack(side="left", padx=(0, 4))
        compact_button(controls, "…", pick, width=22, parent_bg=CARD).pack(side="left")
        if amount_var is not None:
            spin = ttk.Spinbox(
                controls,
                from_=0,
                to=100,
                increment=1,
                textvariable=amount_var,
                width=6,
            )
            spin.pack(side="left", padx=(10, 0))
            ttk.Label(controls, text="%", style="CardMuted.TLabel").pack(side="left", padx=(2, 0))
            if label_text == "Umbral 1":
                self._green_spin = spin
            else:
                self._yellow_spin = spin
        return row + 1

    def _parse_optional_color(self, value: str, field_name: str) -> str | None:
        text = value.strip()
        if not text:
            return None
        if not HEX_COLOR_RE.match(text):
            raise ValueError(field_name)
        return text

    def _parse_required_color(self, value: str, field_name: str) -> str:
        text = value.strip()
        if not HEX_COLOR_RE.match(text):
            raise ValueError(field_name)
        return text

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
        show_daily_tokens = bool(self._daily_tokens_var.get())
        show_plan = bool(self._plan_var.get())
        if not (show_usd or show_tokens or show_daily_tokens or show_plan):
            _win_alert("Activá al menos un modo de visualización del monto.", error=True)
            return

        startup = bool(self._startup_var.get())
        label_x, label_y = self._config.label_x, self._config.label_y
        if self._on_get_label_position:
            label_x, label_y = self._on_get_label_position()

        try:
            label_bg_color = self._parse_optional_color(self._bg_color_var.get(), "color de fondo")
            label_fg_color = self._parse_optional_color(self._fg_color_var.get(), "color de texto")
            threshold_color_low = self._parse_required_color(self._thresh_low_var.get(), "color verde")
            threshold_color_medium = self._parse_required_color(self._thresh_medium_var.get(), "color amarillo")
            threshold_color_high = self._parse_required_color(self._thresh_high_var.get(), "color rojo")
        except ValueError as exc:
            _win_alert(f"Revisá el {exc} (formato #RRGGBB).", error=True)
            return

        updated = AppConfig(
            refresh_interval_seconds=refresh,
            display_mode=self._config.display_mode,
            open_dashboard_on_click=self._config.open_dashboard_on_click,
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
            label_show_daily_tokens=show_daily_tokens,
            label_show_plan=show_plan,
            auto_install_updates=bool(self._auto_install_var.get()),
            label_bg_color=label_bg_color,
            label_fg_color=label_fg_color,
            threshold_color_low=threshold_color_low,
            threshold_color_medium=threshold_color_medium,
            threshold_color_high=threshold_color_high,
            usage_basis=UsageBasis.parse(self._usage_basis_var.get()).value,
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
        self._config = updated

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
