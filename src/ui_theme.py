from __future__ import annotations



import tkinter as tk

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


