from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk



BG = "#111113"

CARD = "#1c1c1f"

BORDER = "#2e2e33"

HOVER = "#2a2a30"

TEXT = "#f4f4f5"

MUTED = "#a1a1aa"

ACCENT = "#7c6cff"

ACCENT_HOVER = "#9488ff"

GREEN = "#22c55e"

YELLOW = "#eab308"

RED = "#ef4444"





def _map_widget_states(style: ttk.Style, name: str, *, bg: str = CARD) -> None:

    style.map(

        name,

        background=[

            ("active", HOVER),

            ("pressed", HOVER),

            ("selected", bg),

            ("!disabled", bg),

        ],

        foreground=[

            ("active", TEXT),

            ("pressed", TEXT),

            ("selected", TEXT),

            ("disabled", MUTED),

            ("!disabled", TEXT),

        ],

        indicatorcolor=[

            ("selected", ACCENT),

            ("pressed", ACCENT),

            ("active", ACCENT),

        ],

        indicatorbackground=[

            ("selected", bg),

            ("pressed", HOVER),

            ("active", HOVER),

            ("!disabled", bg),

        ],

    )





def apply_theme(root: tk.Misc) -> None:

    root.configure(bg=BG)

    style = ttk.Style(root)

    try:

        style.theme_use("clam")

    except tk.TclError:

        pass



    style.configure(".", background=BG, foreground=TEXT, fieldbackground=CARD, bordercolor=BORDER)

    style.configure("TFrame", background=BG)

    style.configure("Card.TFrame", background=CARD, relief="flat")

    style.configure("TLabel", background=BG, foreground=TEXT, font=("Segoe UI", 10))

    style.configure("Title.TLabel", background=BG, foreground=TEXT, font=("Segoe UI Semibold", 16))

    style.configure("Muted.TLabel", background=BG, foreground=MUTED, font=("Segoe UI", 9))

    style.configure("Card.TLabel", background=CARD, foreground=TEXT, font=("Segoe UI", 10))

    style.configure("CardMuted.TLabel", background=CARD, foreground=MUTED, font=("Segoe UI", 9))



    style.configure(

        "Accent.TButton",

        background=ACCENT,

        foreground=TEXT,

        borderwidth=0,

        focusthickness=0,

        focuscolor=CARD,

        font=("Segoe UI Semibold", 10),

        padding=(14, 8),

    )

    style.map("Accent.TButton", background=[("active", ACCENT_HOVER)], foreground=[("active", TEXT)])



    style.configure(

        "Ghost.TButton",

        background=CARD,

        foreground=TEXT,

        borderwidth=1,

        relief="solid",

        focuscolor=CARD,

        font=("Segoe UI", 10),

        padding=(12, 8),

    )

    style.map("Ghost.TButton", background=[("active", HOVER)], foreground=[("active", TEXT)])



    style.configure(

        "TCheckbutton",

        background=CARD,

        foreground=TEXT,

        focuscolor=CARD,

        font=("Segoe UI", 10),

        padding=(4, 6),

    )

    _map_widget_states(style, "TCheckbutton")



    style.configure(

        "TRadiobutton",

        background=CARD,

        foreground=TEXT,

        focuscolor=CARD,

        font=("Segoe UI", 10),

        padding=(4, 4),

    )

    _map_widget_states(style, "TRadiobutton")



    style.configure(

        "TSpinbox",

        fieldbackground=CARD,

        background=CARD,

        foreground=TEXT,

        arrowcolor=TEXT,

        bordercolor=BORDER,

        lightcolor=CARD,

        darkcolor=BORDER,

        insertcolor=TEXT,

    )

    style.map(

        "TSpinbox",

        fieldbackground=[("readonly", CARD), ("!disabled", CARD)],

        foreground=[("!disabled", TEXT)],

        background=[("active", HOVER), ("!disabled", CARD)],

    )



    style.configure("TSeparator", background=BORDER)





def card(parent: tk.Misc, **kwargs) -> ttk.Frame:

    return ttk.Frame(parent, style="Card.TFrame", padding=16, **kwargs)


def _rounded_polygon(canvas: tk.Canvas, x1: int, y1: int, x2: int, y2: int, radius: int, **kwargs) -> int:
    r = min(radius, (x2 - x1) // 2, (y2 - y1) // 2)
    points = [
        x1 + r,
        y1,
        x2 - r,
        y1,
        x2,
        y1,
        x2,
        y1 + r,
        x2,
        y2 - r,
        x2,
        y2,
        x2 - r,
        y2,
        x1 + r,
        y2,
        x1,
        y2,
        x1,
        y2 - r,
        x1,
        y1 + r,
        x1,
        y1,
    ]
    return canvas.create_polygon(points, smooth=True, **kwargs)


def compact_button(
    parent: tk.Misc,
    text: str,
    command: Callable[[], None],
    *,
    accent: bool = False,
    width: int | None = None,
    parent_bg: str = CARD,
) -> tk.Canvas:
    """Low-profile pill button with rounded corners."""
    fill = ACCENT if accent else CARD
    hover = ACCENT_HOVER if accent else HOVER
    font = ("Segoe UI", 9)
    height = 20
    radius = 6
    pad_x = 10

    measure = tk.Label(parent, text=text, font=font)
    measure.update_idletasks()
    text_w = measure.winfo_reqwidth()
    measure.destroy()

    btn_w = width if width is not None else max(text_w + pad_x * 2, 28)
    canvas = tk.Canvas(
        parent,
        width=btn_w,
        height=height,
        highlightthickness=0,
        bd=0,
        bg=parent_bg,
        cursor="hand2",
    )

    def draw(bg: str) -> None:
        canvas.delete("all")
        outline = ACCENT if accent else BORDER
        _rounded_polygon(canvas, 1, 1, btn_w - 1, height - 1, radius, fill=bg, outline=outline)
        canvas.create_text(btn_w // 2, height // 2, text=text, fill=TEXT, font=font)

    draw(fill)
    canvas.bind("<Enter>", lambda _e: draw(hover))
    canvas.bind("<Leave>", lambda _e: draw(fill))
    canvas.bind("<Button-1>", lambda _e: command())
    return canvas


def color_swatch(
    parent: tk.Misc,
    color: str,
    command: Callable[[], None],
    *,
    size: int = 18,
    parent_bg: str = CARD,
) -> tk.Canvas:
    """Small rounded color preview; click opens picker."""
    canvas = tk.Canvas(
        parent,
        width=size,
        height=size,
        highlightthickness=0,
        bd=0,
        bg=parent_bg,
        cursor="hand2",
    )

    def draw(fill: str) -> None:
        canvas.delete("all")
        _rounded_polygon(canvas, 1, 1, size - 1, size - 1, 4, fill=fill, outline=BORDER)

    draw(color)
    canvas._swatch_color = color  # type: ignore[attr-defined]

    def set_color(fill: str) -> None:
        canvas._swatch_color = fill  # type: ignore[attr-defined]
        draw(fill)

    canvas.set_color = set_color  # type: ignore[attr-defined]
    canvas.bind("<Button-1>", lambda _e: command())
    return canvas





def tk_check(parent: tk.Misc, *, text: str, variable: tk.Variable) -> tk.Checkbutton:
    return tk.Checkbutton(
        parent,
        text=text,
        variable=variable,
        bg=CARD,
        fg=TEXT,
        selectcolor=BORDER,
        activebackground=HOVER,
        activeforeground=TEXT,
        highlightthickness=0,
        borderwidth=0,
        font=("Segoe UI", 10),
        anchor="w",
        padx=2,
        pady=4,
    )


def tk_option(parent: tk.Misc, *, text: str, variable: tk.Variable, value: str) -> tk.Radiobutton:

    """Dark-theme radio button with readable hover (ttk is unreliable on Windows)."""

    return tk.Radiobutton(

        parent,

        text=text,

        variable=variable,

        value=value,

        bg=CARD,

        fg=TEXT,

        selectcolor=BORDER,

        activebackground=HOVER,

        activeforeground=TEXT,

        highlightthickness=0,

        borderwidth=0,

        font=("Segoe UI", 10),

        anchor="w",

        padx=2,

        pady=2,

    )


