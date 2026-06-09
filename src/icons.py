from __future__ import annotations

import ctypes
import os
import sys
from ctypes import wintypes
from functools import lru_cache
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw

from .usage_levels import ThresholdColors, UsageLevel, UsageThresholds, usage_level

ICON_SIZE = 64
TRAY_ICON_NAME = "tray-icon.png"
TRIANGLE_SOURCE = (255, 140, 0)
LEVEL_INNER_COLORS = {
    UsageLevel.LOW: (34, 197, 94),
    UsageLevel.MEDIUM: (234, 179, 8),
    UsageLevel.HIGH: (239, 68, 68),
    UsageLevel.UNKNOWN: (113, 113, 122),
}


def _tray_icon_path() -> Path:
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).resolve().parent
    else:
        base = Path(__file__).resolve().parent.parent
    return base / "assets" / TRAY_ICON_NAME


def _cursor_exe_paths() -> list[Path]:
    local = os.environ.get("LOCALAPPDATA", "")
    paths = [
        Path(local) / "Programs" / "cursor" / "Cursor.exe",
        Path(local) / "Programs" / "Cursor" / "Cursor.exe",
        Path(r"C:\Program Files\Cursor\Cursor.exe"),
    ]
    return [path for path in paths if path.exists()]


@lru_cache(maxsize=1)
def _load_tray_icon_base() -> Optional[Image.Image]:
    path = _tray_icon_path()
    if not path.is_file():
        return None
    with Image.open(path) as source:
        return source.convert("RGBA").copy()


def _recolor_triangle(image: Image.Image, rgb: tuple[int, int, int]) -> Image.Image:
    sr, sg, sb = TRIANGLE_SOURCE
    tr, tg, tb = rgb
    out = image.copy()
    pixels = out.load()
    for y in range(out.height):
        for x in range(out.width):
            r, g, b, a = pixels[x, y]
            if a > 200 and abs(r - sr) <= 5 and abs(g - sg) <= 5 and abs(b - sb) <= 5:
                pixels[x, y] = (tr, tg, tb, a)
    return out


def _level_rgb(level: UsageLevel, colors: ThresholdColors | None) -> tuple[int, int, int]:
    if colors is not None:
        return colors.rgb_for(level)
    return LEVEL_INNER_COLORS.get(level, LEVEL_INNER_COLORS[UsageLevel.UNKNOWN])


@lru_cache(maxsize=64)
def _load_tray_brand_icon(
    size: int = ICON_SIZE,
    level: UsageLevel = UsageLevel.UNKNOWN,
    color_key: str = "",
) -> Optional[Image.Image]:
    base = _load_tray_icon_base()
    if base is None:
        return None
    if color_key:
        low, medium, high = color_key.split("|", 2)
        inner = _level_rgb(level, ThresholdColors(low=low, medium=medium, high=high))
    else:
        inner = _level_rgb(level, None)
    image = _recolor_triangle(base, inner)
    if image.size != (size, size):
        image = image.resize((size, size), Image.Resampling.LANCZOS)
    return image


@lru_cache(maxsize=1)
def _load_cursor_brand_icon(size: int = ICON_SIZE) -> Optional[Image.Image]:
    for exe in _cursor_exe_paths():
        icon = _icon_from_exe(exe, size)
        if icon is not None:
            return icon
    return None


def _icon_from_exe(exe_path: Path, size: int) -> Optional[Image.Image]:
    large = wintypes.HICON()
    small = wintypes.HICON()
    extracted = ctypes.windll.shell32.ExtractIconExW(
        str(exe_path), 0, ctypes.byref(large), ctypes.byref(small), 1
    )
    if extracted == 0:
        return None
    handle = large.value or small.value
    if not handle:
        return None
    try:
        return _hicon_to_image(handle, size)
    finally:
        ctypes.windll.user32.DestroyIcon(handle)
        if small.value and small.value != handle:
            ctypes.windll.user32.DestroyIcon(small.value)


def _hicon_to_image(handle: int, size: int) -> Optional[Image.Image]:
    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32

    class ICONINFO(ctypes.Structure):
        _fields_ = [
            ("fIcon", wintypes.BOOL),
            ("xHotspot", wintypes.DWORD),
            ("yHotspot", wintypes.DWORD),
            ("hbmMask", wintypes.HBITMAP),
            ("hbmColor", wintypes.HBITMAP),
        ]

    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [
            ("biSize", wintypes.DWORD),
            ("biWidth", wintypes.LONG),
            ("biHeight", wintypes.LONG),
            ("biPlanes", wintypes.WORD),
            ("biBitCount", wintypes.WORD),
            ("biCompression", wintypes.DWORD),
            ("biSizeImage", wintypes.DWORD),
            ("biXPelsPerMeter", wintypes.LONG),
            ("biYPelsPerMeter", wintypes.LONG),
            ("biClrUsed", wintypes.DWORD),
            ("biClrImportant", wintypes.DWORD),
        ]

    class BITMAPINFO(ctypes.Structure):
        _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", wintypes.DWORD * 3)]

    info = ICONINFO()
    if not user32.GetIconInfo(handle, ctypes.byref(info)):
        return None

    hdc = user32.GetDC(0)
    try:
        bmp_info = BITMAPINFO()
        bmp_info.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmp_info.bmiHeader.biWidth = size
        bmp_info.bmiHeader.biHeight = -size
        bmp_info.bmiHeader.biPlanes = 1
        bmp_info.bmiHeader.biBitCount = 32

        buffer = (ctypes.c_ubyte * (size * size * 4))()
        drawn = user32.DrawIconEx(hdc, 0, 0, handle, size, size, 0, 0, 0x0003)
        if not drawn:
            return None

        hbmp = gdi32.CreateCompatibleBitmap(hdc, size, size)
        memdc = gdi32.CreateCompatibleDC(hdc)
        old = gdi32.SelectObject(memdc, hbmp)
        user32.DrawIconEx(memdc, 0, 0, handle, size, size, 0, 0, 0x0003)
        gdi32.GetDIBits(memdc, hbmp, 0, size, buffer, ctypes.byref(bmp_info), 0)
        gdi32.SelectObject(memdc, old)
        gdi32.DeleteDC(memdc)
        gdi32.DeleteObject(hbmp)

        image = Image.frombuffer("RGBA", (size, size), bytes(buffer), "raw", "BGRA", 0, 1)
        return image
    finally:
        user32.ReleaseDC(0, hdc)
        if info.hbmColor:
            gdi32.DeleteObject(info.hbmColor)
        if info.hbmMask:
            gdi32.DeleteObject(info.hbmMask)


def _draw_fallback_icon(level: UsageLevel = UsageLevel.LOW, colors: ThresholdColors | None = None) -> Image.Image:
    rgb = _level_rgb(level, colors)
    fill = (*rgb, 255)
    image = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((2, 2, ICON_SIZE - 2, ICON_SIZE - 2), fill=fill)
    cursor = _load_cursor_brand_icon(40)
    if cursor is not None:
        image.alpha_composite(cursor, (12, 12))
        return image
    draw.rounded_rectangle((18, 18, 46, 46), radius=8, fill=(20, 20, 20, 255))
    draw.polygon([(24, 34), (34, 24), (40, 38), (32, 38)], fill=(240, 240, 240, 255))
    return image


def _color_cache_key(colors: ThresholdColors | None) -> str:
    if colors is None:
        return ""
    return f"{colors.low}|{colors.medium}|{colors.high}"


def _brand_icon(level: UsageLevel, colors: ThresholdColors | None = None) -> Image.Image:
    color_key = _color_cache_key(colors)
    brand = _load_tray_brand_icon(ICON_SIZE, level, color_key)
    if brand is not None:
        return brand
    return _draw_fallback_icon(level, colors)


def make_tray_icon(
    usage_percent: float | None = None,
    *,
    error: bool = False,
    thresholds: UsageThresholds | None = None,
    colors: ThresholdColors | None = None,
    amount_usd: float | None = None,
) -> Image.Image:
    if error:
        return _brand_icon(UsageLevel.HIGH, colors)

    pct = usage_percent if usage_percent is not None else amount_usd
    level = usage_level(pct, thresholds)
    return _brand_icon(level, colors)
