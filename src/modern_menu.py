from __future__ import annotations

import ctypes
import tkinter as tk
from ctypes import wintypes
from typing import Callable, Iterable, Optional

from .ui_theme import BG, BORDER, CARD, TEXT

user32 = ctypes.windll.user32
HWND_TOPMOST = -1
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040
MENU_Z_ORDER_MS = 100


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


def pointer_xy(fallback_x: int, fallback_y: int) -> tuple[int, int]:
    pt = POINT()
    if user32.GetCursorPos(ctypes.byref(pt)):
        return int(pt.x), int(pt.y)
    return fallback_x, fallback_y


def _place_win32_topmost(window: tk.Misc, x: int, y: int) -> None:
    window.update_idletasks()
    width = max(window.winfo_width(), 1)
    height = max(window.winfo_height(), 1)
    window.geometry(f"+{x}+{y}")
    window.update_idletasks()
    window.attributes("-topmost", True)
    user32.SetWindowPos(
        window.winfo_id(),
        HWND_TOPMOST,
        int(x),
        int(y),
        int(width),
        int(height),
        SWP_NOACTIVATE | SWP_SHOWWINDOW,
    )


class MenuAction:
    def __init__(self, label: str, command: Callable[[], None], *, destructive: bool = False) -> None:
        self.label = label
        self.command = command
        self.destructive = destructive


class ModernPopupMenu:
    def __init__(self, parent: tk.Misc) -> None:
        self._parent = parent
        self._window: tk.Toplevel | None = None
        self._on_closed: Optional[Callable[[], None]] = None
        self._z_order_job: str | None = None
        self._menu_x = 0
        self._menu_y = 0

    def show(
        self,
        x: int,
        y: int,
        actions: Iterable[MenuAction],
        *,
        on_closed: Optional[Callable[[], None]] = None,
    ) -> None:
        self.close()
        self._on_closed = on_closed

        if x <= 0 and y <= 0:
            x, y = pointer_xy(x, y)

        win = tk.Toplevel(self._parent)
        win.overrideredirect(True)
        win.configure(bg=BORDER)
        self._window = win

        frame = tk.Frame(win, bg=BORDER, padx=1, pady=1)
        frame.pack()

        inner = tk.Frame(frame, bg=CARD)
        inner.pack()

        for action in actions:
            if action.label == "---":
                tk.Frame(inner, bg=BORDER, height=1).pack(fill="x", padx=10, pady=4)
                continue
            fg = "#ff8a80" if action.destructive else TEXT
            btn = tk.Label(
                inner,
                text=action.label,
                bg=CARD,
                fg=fg,
                font=("Segoe UI", 10),
                anchor="w",
                padx=14,
                pady=8,
                cursor="hand2",
            )
            btn.pack(fill="x")

            def on_enter(event: tk.Event, widget: tk.Label = btn, color: str = fg) -> None:
                widget.configure(bg="#2a2a30", fg=color)

            def on_leave(event: tk.Event, widget: tk.Label = btn, color: str = fg) -> None:
                widget.configure(bg=CARD, fg=color)

            def on_click(_event: tk.Event, cmd: Callable[[], None] = action.command) -> None:
                self.close()
                cmd()

            btn.bind("<Enter>", on_enter)
            btn.bind("<Leave>", on_leave)
            btn.bind("<Button-1>", on_click)

        win.update_idletasks()
        width = win.winfo_width()
        height = win.winfo_height()
        screen_w = win.winfo_screenwidth()
        screen_h = win.winfo_screenheight()
        if x + width > screen_w:
            x = max(0, screen_w - width - 8)
        if y + height > screen_h:
            y = max(0, screen_h - height - 8)

        self._menu_x = int(x)
        self._menu_y = int(y)
        _place_win32_topmost(win, self._menu_x, self._menu_y)
        self._schedule_z_order_refresh()

        win.bind("<FocusOut>", lambda _e: self.close())
        win.focus_force()

    def _schedule_z_order_refresh(self) -> None:
        if self._window is None:
            return
        _place_win32_topmost(self._window, self._menu_x, self._menu_y)
        self._z_order_job = self._window.after(MENU_Z_ORDER_MS, self._schedule_z_order_refresh)

    def close(self) -> None:
        callback = self._on_closed
        self._on_closed = None

        if self._window is not None:
            if self._z_order_job is not None:
                try:
                    self._window.after_cancel(self._z_order_job)
                except tk.TclError:
                    pass
                self._z_order_job = None
            try:
                self._window.destroy()
            except tk.TclError:
                pass
            self._window = None

        if callback:
            callback()
