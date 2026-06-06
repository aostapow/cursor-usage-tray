from __future__ import annotations

import ctypes
import os
from ctypes import wintypes
from functools import lru_cache
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

from .usage_levels import UsageLevel, UsageThresholds, usage_level

ICON_SIZE = 64


def _cursor_exe_paths() -> list[Path]:
    local = os.environ.get("LOCALAPPDATA", "")
    paths = [
        Path(local) / "Programs" / "cursor" / "Cursor.exe",
        Path(local) / "Programs" / "Cursor" / "Cursor.exe",
        Path(r"C:\Program Files\Cursor\Cursor.exe"),
    ]
    return [path for path in paths if path.exists()]


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


def _draw_amount_badge(amount_usd: float, level: UsageLevel) -> Image.Image:
    colors = {
        UsageLevel.LOW: (34, 197, 94, 255),
        UsageLevel.MEDIUM: (234, 179, 8, 255),
        UsageLevel.HIGH: (239, 68, 68, 255),
        UsageLevel.UNKNOWN: (113, 113, 122, 255),
    }
    bg = colors.get(level, colors[UsageLevel.UNKNOWN])
    image = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((4, 4, ICON_SIZE - 4, ICON_SIZE - 4), fill=bg)
    label = f"{amount_usd:.0f}" if amount_usd >= 100 else f"{amount_usd:.1f}".rstrip("0").rstrip(".")
    if len(label) > 5:
        label = label[:5]
    try:
        font = ImageFont.truetype("segoeui.ttf", 16)
    except OSError:
        try:
            font = ImageFont.truetype("arial.ttf", 16)
        except OSError:
            font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), label, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((ICON_SIZE - tw) / 2, (ICON_SIZE - th) / 2 - 2), label, fill="white", font=font)
    return image


def _draw_cursor_on_green() -> Image.Image:
    image = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((2, 2, ICON_SIZE - 2, ICON_SIZE - 2), fill=(34, 197, 94, 255))
    brand = _load_cursor_brand_icon(40)
    if brand is not None:
        image.alpha_composite(brand, (12, 12))
        return image
    draw.rounded_rectangle((18, 18, 46, 46), radius=8, fill=(20, 20, 20, 255))
    draw.polygon([(24, 34), (34, 24), (40, 38), (32, 38)], fill=(240, 240, 240, 255))
    return image


def make_tray_icon(
    amount_usd: float | None = None,
    *,
    error: bool = False,
    thresholds: UsageThresholds | None = None,
) -> Image.Image:
    if error:
        image = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.ellipse((4, 4, ICON_SIZE - 4, ICON_SIZE - 4), fill=(239, 68, 68, 255))
        try:
            font = ImageFont.truetype("segoeui.ttf", 24)
        except OSError:
            font = ImageFont.load_default()
        draw.text((22, 14), "!", fill="white", font=font)
        return image

    level = usage_level(amount_usd, thresholds)
    if level == UsageLevel.LOW:
        return _draw_cursor_on_green()
    if amount_usd is None:
        image = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.ellipse((4, 4, ICON_SIZE - 4, ICON_SIZE - 4), fill=(113, 113, 122, 255))
        try:
            font = ImageFont.truetype("segoeui.ttf", 22)
        except OSError:
            font = ImageFont.load_default()
        draw.text((20, 14), "?", fill="white", font=font)
        return image
    return _draw_amount_badge(amount_usd, level)
