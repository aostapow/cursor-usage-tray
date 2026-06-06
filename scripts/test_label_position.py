"""Smoke tests for floating label positioning (no GUI mainloop)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.taskbar_label import (  # noqa: E402
    _clamp_to_screen,
    _taskbar_rect,
    default_label_position,
)
from src.usage_levels import UsageThresholds, usage_level  # noqa: E402


def test_default_position_on_screen() -> None:
    width, height = 93, 28
    x, y = default_label_position(width, height)
    cx, cy = _clamp_to_screen(x, y, width, height)
    assert (x, y) == (cx, cy), "default position must be on screen"


def test_floating_can_use_taskbar_area() -> None:
    taskbar = _taskbar_rect()
    width, height = 80, 28
    center_x = taskbar.left + (taskbar.right - taskbar.left - width) // 2
    center_y = taskbar.top + 2
    x, y = _clamp_to_screen(center_x, center_y, width, height)
    assert y >= taskbar.top


def test_thresholds_configurable() -> None:
    t = UsageThresholds(green_max=10, yellow_max=25).normalized()
    assert usage_level(9, t).value == "low"
    assert usage_level(20, t).value == "medium"
    assert usage_level(30, t).value == "high"


def main() -> int:
    test_default_position_on_screen()
    test_floating_can_use_taskbar_area()
    test_thresholds_configurable()
    print("OK: all positioning tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
