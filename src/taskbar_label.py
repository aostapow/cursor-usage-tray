from __future__ import annotations

import ctypes
import tkinter as tk
import winreg
from ctypes import wintypes
from typing import Callable, Optional

from .usage_levels import UsageThresholds, usage_style

user32 = ctypes.windll.user32
shell32 = ctypes.windll.shell32
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:  # noqa: BLE001
    try:
        user32.SetProcessDPIAware()
    except Exception:  # noqa: BLE001
        pass


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


class APPBARDATA(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("hWnd", wintypes.HWND),
        ("uCallbackMessage", wintypes.UINT),
        ("uEdge", wintypes.UINT),
        ("rc", RECT),
        ("lParam", wintypes.LPARAM),
    ]


ABM_GETTASKBARPOS = 5
GWL_EXSTYLE = -20
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080
HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
DRAG_THRESHOLD_PX = 4
CLOCK_CLASS_NAMES = frozenset({"TrayClockWClass", "ClockButton"})
CLOCK_GAP_PX = 8
BOUNDS_CHECK_MS = 2000
Z_ORDER_REFRESH_MS = 300


def _system_uses_light_theme() -> bool:
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        ) as key:
            value, _ = winreg.QueryValueEx(key, "SystemUsesLightTheme")
            return bool(value)
    except OSError:
        return False


def _taskbar_rect() -> RECT:
    data = APPBARDATA()
    data.cbSize = ctypes.sizeof(APPBARDATA)
    shell32.SHAppBarMessage(ABM_GETTASKBARPOS, ctypes.byref(data))
    return data.rc


def _virtual_screen_rect() -> RECT:
    left = user32.GetSystemMetrics(76)
    top = user32.GetSystemMetrics(77)
    width = user32.GetSystemMetrics(78)
    height = user32.GetSystemMetrics(79)
    return RECT(left, top, left + width, top + height)


def _find_clock_hwnd_recursive(root_hwnd: int) -> Optional[int]:
    found: list[int] = []
    stack = [root_hwnd]
    while stack:
        parent = stack.pop()
        child = user32.FindWindowExW(parent, None, None, None)
        while child:
            class_name = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(child, class_name, 256)
            if class_name.value in CLOCK_CLASS_NAMES and user32.IsWindowVisible(child):
                found.append(child)
            stack.append(child)
            child = user32.FindWindowExW(parent, child, None, None)
    if not found:
        return None

    def _right_edge(hwnd: int) -> int:
        rect = RECT()
        return rect.right if user32.GetWindowRect(hwnd, ctypes.byref(rect)) else 0

    return max(found, key=_right_edge)


def _find_clock_rect() -> Optional[RECT]:
    tray = user32.FindWindowW("Shell_TrayWnd", None)
    if not tray:
        return None
    clock_hwnd = _find_clock_hwnd_recursive(tray)
    if clock_hwnd:
        rect = RECT()
        return rect if user32.GetWindowRect(clock_hwnd, ctypes.byref(rect)) else None
    notify = user32.FindWindowExW(tray, None, "TrayNotifyWnd", None)
    if notify:
        clock_hwnd = _find_clock_hwnd_recursive(notify)
        if clock_hwnd:
            rect = RECT()
            return rect if user32.GetWindowRect(clock_hwnd, ctypes.byref(rect)) else None
    return None


def _clamp_to_screen(x: int, y: int, width: int, height: int) -> tuple[int, int]:
    screen = _virtual_screen_rect()
    x = max(screen.left, min(x, screen.right - width))
    y = max(screen.top, min(y, screen.bottom - height))
    return x, y


def default_label_position(width: int, height: int) -> tuple[int, int]:
    """Suggested starting point near the taskbar clock (user can drag elsewhere)."""
    clock = _find_clock_rect()
    taskbar = _taskbar_rect()
    if clock:
        x = clock.left - width - CLOCK_GAP_PX
        y = clock.top + max(0, ((clock.bottom - clock.top) - height) // 2)
    else:
        x = taskbar.right - width - 150
        y = taskbar.top + max(0, ((taskbar.bottom - taskbar.top) - height) // 2)
    return _clamp_to_screen(x, y, width, height)


def _apply_win32_styles(hwnd: int) -> None:
    style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW)


class TaskbarLabel:
    """Floating on-screen usage label; drag to move, position is persisted."""

    def __init__(
        self,
        *,
        initial_x: int | None = None,
        initial_y: int | None = None,
        thresholds: UsageThresholds | None = None,
        on_position_changed: Optional[Callable[[int, int], None]] = None,
        on_left_click: Optional[Callable[[], None]] = None,
        on_right_click: Optional[Callable[[tk.Event], None]] = None,
    ) -> None:
        self._on_position_changed = on_position_changed
        self._on_left_click = on_left_click
        self._on_right_click = on_right_click
        self._closed = False
        self._saved_x = initial_x
        self._saved_y = initial_y
        self._thresholds = (thresholds or UsageThresholds()).normalized()
        self._drag_origin: tuple[int, int] | None = None
        self._drag_moved = False
        self._raise_paused = False
        light = _system_uses_light_theme()
        self._bg = "#f3f3f3" if light else "#202020"

        self.root = tk.Tk()
        self.root.withdraw()
        self.root.overrideredirect(True)
        self.root.configure(bg=self._bg)

        self._label = tk.Label(
            self.root,
            text="$-.--",
            font=("Segoe UI Semibold", 12),
            fg="#ffffff",
            bg=self._bg,
            padx=6,
            pady=2,
            cursor="hand2",
        )
        self._label.pack()

        for widget in (self.root, self._label):
            widget.bind("<Button-1>", self._on_drag_start)
            widget.bind("<B1-Motion>", self._on_drag_motion)
            widget.bind("<ButtonRelease-1>", self._on_drag_release)
            widget.bind("<Button-3>", self._handle_right_click)

        self.root.update_idletasks()
        _apply_win32_styles(self.root.winfo_id())
        self._place_initial()
        self.root.deiconify()
        self.root.lift()
        self._schedule_maintenance()
        self._schedule_z_order_refresh()

    def _measure_size(self) -> tuple[int, int]:
        self.root.update_idletasks()
        width = max(self.root.winfo_width(), self._label.winfo_reqwidth() + 12, 48)
        height = max(self.root.winfo_height(), 28)
        return width, height

    def pause_front(self) -> None:
        if self._closed:
            return
        self._raise_paused = True
        hwnd = self.root.winfo_id()
        self.root.attributes("-topmost", False)
        user32.SetWindowPos(
            hwnd,
            HWND_NOTOPMOST,
            0,
            0,
            0,
            0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE,
        )

    def resume_front(self) -> None:
        self._raise_paused = False
        self._bring_to_front()

    def _bring_to_front(self) -> None:
        if self._closed or self._raise_paused:
            return
        hwnd = self.root.winfo_id()
        self.root.attributes("-topmost", True)
        user32.SetWindowPos(
            hwnd,
            HWND_TOPMOST,
            0,
            0,
            0,
            0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW,
        )

    def _win32_place(self, x: int, y: int, width: int, height: int) -> None:
        hwnd = self.root.winfo_id()
        self.root.attributes("-topmost", True)
        user32.SetWindowPos(
            hwnd,
            HWND_TOPMOST,
            x,
            y,
            width,
            height,
            SWP_NOACTIVATE | SWP_SHOWWINDOW,
        )

    def _place_at(self, x: int, y: int, width: int | None = None, height: int | None = None) -> None:
        if width is None or height is None:
            width, height = self._measure_size()
        x, y = _clamp_to_screen(x, y, width, height)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.update_idletasks()
        self._win32_place(x, y, width, height)

    def _resolved_position(self, width: int, height: int) -> tuple[int, int]:
        if self._saved_x is not None and self._saved_y is not None:
            return _clamp_to_screen(self._saved_x, self._saved_y, width, height)
        return default_label_position(width, height)

    def _place_initial(self) -> None:
        width, height = self._measure_size()
        x, y = self._resolved_position(width, height)
        self._place_at(x, y, width, height)

    def current_position(self) -> tuple[int, int]:
        return int(self.root.winfo_x()), int(self.root.winfo_y())

    def apply_saved_position(self, x: int, y: int) -> None:
        self._saved_x = x
        self._saved_y = y
        width, height = self._measure_size()
        px, py = self._resolved_position(width, height)
        self._place_at(px, py, width, height)

    def set_left_click_handler(self, handler: Optional[Callable[[], None]]) -> None:
        self._on_left_click = handler

    def _persist_position(self) -> None:
        if self._closed:
            return
        x = int(self.root.winfo_x())
        y = int(self.root.winfo_y())
        self._saved_x = x
        self._saved_y = y
        if self._on_position_changed:
            self._on_position_changed(x, y)

    def reset_position(self) -> None:
        width, height = self._measure_size()
        x, y = default_label_position(width, height)
        self._place_at(x, y, width, height)
        self._persist_position()

    def _on_drag_start(self, event: tk.Event) -> None:
        self._drag_origin = (event.x_root, event.y_root)
        self._drag_moved = False

    def _on_drag_motion(self, event: tk.Event) -> None:
        if self._drag_origin is None:
            return
        dx = event.x_root - self._drag_origin[0]
        dy = event.y_root - self._drag_origin[1]
        if not self._drag_moved and abs(dx) < DRAG_THRESHOLD_PX and abs(dy) < DRAG_THRESHOLD_PX:
            return
        self._drag_moved = True
        self._label.configure(cursor="fleur")
        width, height = self._measure_size()
        x = int(self.root.winfo_x() + dx)
        y = int(self.root.winfo_y() + dy)
        self._place_at(x, y, width, height)
        self._drag_origin = (event.x_root, event.y_root)

    def _on_drag_release(self, _event: tk.Event) -> None:
        self._label.configure(cursor="hand2")
        if self._drag_moved:
            self._persist_position()
        elif self._on_left_click:
            self._on_left_click()
        self._drag_origin = None
        self._drag_moved = False

    def _handle_right_click(self, event: tk.Event) -> None:
        if self._on_right_click:
            self._on_right_click(event)

    def _schedule_z_order_refresh(self) -> None:
        if self._closed:
            return
        self._bring_to_front()
        self.root.after(Z_ORDER_REFRESH_MS, self._schedule_z_order_refresh)

    def _schedule_maintenance(self) -> None:
        if self._closed:
            return
        self._bring_to_front()
        self._ensure_on_screen()
        self.root.after(BOUNDS_CHECK_MS, self._schedule_maintenance)

    def _ensure_on_screen(self) -> None:
        width, height = self._measure_size()
        x = int(self.root.winfo_x())
        y = int(self.root.winfo_y())
        clamped_x, clamped_y = _clamp_to_screen(x, y, width, height)
        if clamped_x != x or clamped_y != y:
            self._place_at(clamped_x, clamped_y, width, height)
            self._persist_position()

    def update(
        self,
        text: str,
        *,
        amount_usd: float | None = None,
        tooltip: str = "",
        thresholds: UsageThresholds | None = None,
    ) -> None:
        if thresholds is not None:
            self._thresholds = thresholds.normalized()
        style = usage_style(amount_usd, self._thresholds)
        self._label.configure(text=text, fg=style.fg, bg=self._bg)
        self.root.configure(bg=self._bg)
        if tooltip:
            self._label.configure(cursor="hand2")
        width, height = self._measure_size()
        self._place_at(int(self.root.winfo_x()), int(self.root.winfo_y()), width, height)

    def set_thresholds(self, thresholds: UsageThresholds) -> None:
        self._thresholds = thresholds.normalized()
        self.update(self._label.cget("text"), thresholds=self._thresholds)

    def set_visible(self, visible: bool) -> None:
        if self._closed:
            return
        if visible:
            self.root.deiconify()
            self._bring_to_front()
        else:
            self.root.withdraw()

    def run(self) -> None:
        if not self._closed:
            self.root.mainloop()

    def close(self) -> None:
        if self._closed:
            return
        self._persist_position()
        self._closed = True

        def _shutdown() -> None:
            self.root.destroy()

        try:
            self.root.after(0, _shutdown)
        except tk.TclError:
            pass
