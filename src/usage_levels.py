from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

HEX_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")

DEFAULT_THRESHOLD_GREEN_MAX = 10.0
DEFAULT_THRESHOLD_YELLOW_MAX = 20.0
DEFAULT_THRESHOLD_COLOR_LOW = "#008000"
DEFAULT_THRESHOLD_COLOR_MEDIUM = "#ffff00"
DEFAULT_THRESHOLD_COLOR_HIGH = "#ff0000"
DEFAULT_LABEL_FG = "#d4d4d8"


class UsageLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class UsageThresholds:
    green_max: float = DEFAULT_THRESHOLD_GREEN_MAX
    yellow_max: float = DEFAULT_THRESHOLD_YELLOW_MAX

    def normalized(self) -> "UsageThresholds":
        green = max(0.0, min(100.0, float(self.green_max)))
        yellow = max(green, min(100.0, float(self.yellow_max)))
        return UsageThresholds(green_max=green, yellow_max=yellow)


@dataclass(frozen=True)
class ThresholdColors:
    low: str = DEFAULT_THRESHOLD_COLOR_LOW
    medium: str = DEFAULT_THRESHOLD_COLOR_MEDIUM
    high: str = DEFAULT_THRESHOLD_COLOR_HIGH

    def fg_for(self, level: UsageLevel) -> str:
        if level == UsageLevel.LOW:
            return self.low
        if level == UsageLevel.MEDIUM:
            return self.medium
        if level == UsageLevel.HIGH:
            return self.high
        return DEFAULT_LABEL_FG

    def rgb_for(self, level: UsageLevel) -> tuple[int, int, int]:
        return hex_to_rgb(self.fg_for(level))


@dataclass(frozen=True)
class UsageStyle:
    level: UsageLevel
    fg: str
    bg: str
    accent: str


_STYLES = {
    UsageLevel.LOW: UsageStyle(UsageLevel.LOW, "#008000", "#1a3d22", "#22c55e"),
    UsageLevel.MEDIUM: UsageStyle(UsageLevel.MEDIUM, "#ffff00", "#4a3b12", "#eab308"),
    UsageLevel.HIGH: UsageStyle(UsageLevel.HIGH, "#ff0000", "#4a1714", "#ef4444"),
    UsageLevel.UNKNOWN: UsageStyle(UsageLevel.UNKNOWN, "#d4d4d8", "#27272a", "#71717a"),
}


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    if not HEX_COLOR_RE.match(hex_color):
        raise ValueError(f"invalid hex color: {hex_color!r}")
    return int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)


def usage_level(usage_percent: float | None, thresholds: UsageThresholds | None = None) -> UsageLevel:
    if usage_percent is None:
        return UsageLevel.UNKNOWN
    t = (thresholds or UsageThresholds()).normalized()
    if usage_percent < t.green_max:
        return UsageLevel.LOW
    if usage_percent <= t.yellow_max:
        return UsageLevel.MEDIUM
    return UsageLevel.HIGH


def usage_style(
    usage_percent: float | None,
    thresholds: UsageThresholds | None = None,
    colors: ThresholdColors | None = None,
) -> UsageStyle:
    level = usage_level(usage_percent, thresholds)
    base = _STYLES[level]
    if colors is None:
        return base
    return UsageStyle(level, colors.fg_for(level), base.bg, base.accent)
