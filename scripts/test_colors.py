"""Unit tests for configurable label and threshold colors (no GUI)."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import AppConfig  # noqa: E402
from src.usage_levels import (  # noqa: E402
    DEFAULT_LABEL_FG,
    DEFAULT_THRESHOLD_COLOR_HIGH,
    DEFAULT_THRESHOLD_COLOR_LOW,
    DEFAULT_THRESHOLD_COLOR_MEDIUM,
    ThresholdColors,
    UsageLevel,
    UsageThresholds,
    hex_to_rgb,
    usage_level,
    usage_style,
)


def test_threshold_colors_fg_for_levels() -> None:
    colors = ThresholdColors(low="#111111", medium="#222222", high="#333333")
    assert colors.fg_for(UsageLevel.LOW) == "#111111"
    assert colors.fg_for(UsageLevel.MEDIUM) == "#222222"
    assert colors.fg_for(UsageLevel.HIGH) == "#333333"
    assert colors.fg_for(UsageLevel.UNKNOWN) == DEFAULT_LABEL_FG


def test_hex_to_rgb() -> None:
    assert hex_to_rgb("#9ef0a5") == (158, 240, 165)
    try:
        hex_to_rgb("bad")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for invalid hex")


def test_usage_style_custom_colors() -> None:
    thresholds = UsageThresholds(green_max=10, yellow_max=20).normalized()
    colors = ThresholdColors(low="#00ff00", medium="#ffff00", high="#ff0000")
    style = usage_style(5, thresholds, colors)
    assert style.fg == "#00ff00"
    style = usage_style(15, thresholds, colors)
    assert style.fg == "#ffff00"
    style = usage_style(25, thresholds, colors)
    assert style.fg == "#ff0000"


def test_usage_level_boundaries() -> None:
    t = UsageThresholds(green_max=10, yellow_max=25).normalized()
    assert usage_level(9, t) == UsageLevel.LOW
    assert usage_level(20, t) == UsageLevel.MEDIUM
    assert usage_level(30, t) == UsageLevel.HIGH


def test_config_color_roundtrip() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        config_path = Path(tmp) / "config.json"
        app_dir = Path(tmp)

        with patch("src.config.CONFIG_PATH", config_path), patch("src.config.APP_DIR", app_dir):
            original = AppConfig(
                label_bg_color="#101010",
                label_fg_color="#abcdef",
                threshold_color_low="#111111",
                threshold_color_medium="#222222",
                threshold_color_high="#333333",
            )
            original.save()
            loaded = AppConfig.load()
            assert loaded.label_bg_color == "#101010"
            assert loaded.label_fg_color == "#abcdef"
            assert loaded.threshold_color_low == "#111111"
            assert loaded.threshold_color_medium == "#222222"
            assert loaded.threshold_color_high == "#333333"


def test_config_null_colors() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        config_path = Path(tmp) / "config.json"
        app_dir = Path(tmp)
        config_path.write_text(
            json.dumps({"label_bg_color": None, "label_fg_color": None}),
            encoding="utf-8",
        )

        with patch("src.config.CONFIG_PATH", config_path), patch("src.config.APP_DIR", app_dir):
            loaded = AppConfig.load()
            assert loaded.label_bg_color is None
            assert loaded.label_fg_color is None
            assert loaded.resolved_label_fg() == DEFAULT_LABEL_FG
            assert loaded.threshold_colors() == ThresholdColors(
                low=DEFAULT_THRESHOLD_COLOR_LOW,
                medium=DEFAULT_THRESHOLD_COLOR_MEDIUM,
                high=DEFAULT_THRESHOLD_COLOR_HIGH,
            )


def main() -> int:
    test_threshold_colors_fg_for_levels()
    test_hex_to_rgb()
    test_usage_style_custom_colors()
    test_usage_level_boundaries()
    test_config_color_roundtrip()
    test_config_null_colors()
    print("OK: all color tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
