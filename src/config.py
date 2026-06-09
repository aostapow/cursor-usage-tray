from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from .usage_basis import UsageBasis
from .usage_levels import (
    DEFAULT_LABEL_FG,
    DEFAULT_THRESHOLD_COLOR_HIGH,
    DEFAULT_THRESHOLD_COLOR_LOW,
    DEFAULT_THRESHOLD_COLOR_MEDIUM,
    DEFAULT_THRESHOLD_GREEN_MAX,
    DEFAULT_THRESHOLD_YELLOW_MAX,
    ThresholdColors,
    UsageThresholds,
)

APP_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "cursor-usage-tray"
CONFIG_PATH = APP_DIR / "config.json"
DEFAULT_REFRESH_SECONDS = 90
DEFAULT_LABEL_X = 1402
DEFAULT_LABEL_Y = 1036
DEFAULT_LABEL_ALTERNATE_SECONDS = 10


def _load_label_coord(data: dict, key: str) -> int | None:
    if key not in data:
        return DEFAULT_LABEL_X if key == "label_x" else DEFAULT_LABEL_Y
    value = data.get(key)
    return int(value) if value is not None else None


@dataclass
class AppConfig:
    refresh_interval_seconds: int = DEFAULT_REFRESH_SECONDS
    display_mode: str = "on_demand_usd"
    open_dashboard_on_click: bool = False
    show_taskbar_label: bool = True
    show_tray_icon: bool = True
    start_with_windows: bool = True
    label_x: int | None = DEFAULT_LABEL_X
    label_y: int | None = DEFAULT_LABEL_Y
    threshold_green_max: float = DEFAULT_THRESHOLD_GREEN_MAX
    threshold_yellow_max: float = DEFAULT_THRESHOLD_YELLOW_MAX
    label_alternate_seconds: int = DEFAULT_LABEL_ALTERNATE_SECONDS
    label_show_usd: bool = True
    label_show_tokens: bool = True
    label_show_daily_tokens: bool = False
    label_show_plan: bool = True
    auto_install_updates: bool = False
    label_bg_color: str | None = None
    label_fg_color: str | None = None
    threshold_color_low: str = DEFAULT_THRESHOLD_COLOR_LOW
    threshold_color_medium: str = DEFAULT_THRESHOLD_COLOR_MEDIUM
    threshold_color_high: str = DEFAULT_THRESHOLD_COLOR_HIGH
    usage_basis: str = UsageBasis.ON_DEMAND.value

    def usage_basis_enum(self) -> UsageBasis:
        return UsageBasis.parse(self.usage_basis)

    def usage_thresholds(self) -> UsageThresholds:
        return UsageThresholds(
            green_max=self.threshold_green_max,
            yellow_max=self.threshold_yellow_max,
        ).normalized()

    def threshold_colors(self) -> ThresholdColors:
        return ThresholdColors(
            low=self.threshold_color_low,
            medium=self.threshold_color_medium,
            high=self.threshold_color_high,
        )

    def resolved_label_bg(self) -> str:
        if self.label_bg_color:
            return self.label_bg_color
        from .taskbar_label import default_label_bg

        return default_label_bg()

    def resolved_label_fg(self) -> str:
        return self.label_fg_color or DEFAULT_LABEL_FG

    @classmethod
    def load(cls) -> "AppConfig":
        if not CONFIG_PATH.exists():
            return cls()
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        label_bg = data.get("label_bg_color")
        label_fg = data.get("label_fg_color")
        config = cls(
            refresh_interval_seconds=max(60, int(data.get("refresh_interval_seconds", DEFAULT_REFRESH_SECONDS))),
            display_mode=str(data.get("display_mode", "on_demand_usd")),
            open_dashboard_on_click=bool(data.get("open_dashboard_on_click", False)),
            show_taskbar_label=True,
            show_tray_icon=True,
            start_with_windows=bool(data.get("start_with_windows", True)),
            label_x=_load_label_coord(data, "label_x"),
            label_y=_load_label_coord(data, "label_y"),
            threshold_green_max=float(data.get("threshold_green_max", DEFAULT_THRESHOLD_GREEN_MAX)),
            threshold_yellow_max=float(data.get("threshold_yellow_max", DEFAULT_THRESHOLD_YELLOW_MAX)),
            label_alternate_seconds=max(0, int(data.get("label_alternate_seconds", DEFAULT_LABEL_ALTERNATE_SECONDS))),
            label_show_usd=bool(data.get("label_show_usd", True)),
            label_show_tokens=bool(data.get("label_show_tokens", True)),
            label_show_daily_tokens=bool(data.get("label_show_daily_tokens", False)),
            label_show_plan=bool(data.get("label_show_plan", True)),
            auto_install_updates=bool(data.get("auto_install_updates", False)),
            label_bg_color=str(label_bg) if label_bg else None,
            label_fg_color=str(label_fg) if label_fg else None,
            threshold_color_low=str(data.get("threshold_color_low", DEFAULT_THRESHOLD_COLOR_LOW)),
            threshold_color_medium=str(data.get("threshold_color_medium", DEFAULT_THRESHOLD_COLOR_MEDIUM)),
            threshold_color_high=str(data.get("threshold_color_high", DEFAULT_THRESHOLD_COLOR_HIGH)),
            usage_basis=str(data.get("usage_basis", UsageBasis.ON_DEMAND.value)),
        )
        if "session_token" in data or data.get("show_tray_icon") is False or "label_mode" in data:
            config.save()
        return config

    def save(self) -> None:
        APP_DIR.mkdir(parents=True, exist_ok=True)
        thresholds = self.usage_thresholds()
        CONFIG_PATH.write_text(
            json.dumps(
                {
                    "refresh_interval_seconds": self.refresh_interval_seconds,
                    "display_mode": self.display_mode,
                    "open_dashboard_on_click": self.open_dashboard_on_click,
                    "show_taskbar_label": True,
                    "show_tray_icon": self.show_tray_icon,
                    "start_with_windows": self.start_with_windows,
                    "label_x": self.label_x,
                    "label_y": self.label_y,
                    "threshold_green_max": thresholds.green_max,
                    "threshold_yellow_max": thresholds.yellow_max,
                    "label_alternate_seconds": self.label_alternate_seconds,
                    "label_show_usd": self.label_show_usd,
                    "label_show_tokens": self.label_show_tokens,
                    "label_show_daily_tokens": self.label_show_daily_tokens,
                    "label_show_plan": self.label_show_plan,
                    "auto_install_updates": self.auto_install_updates,
                    "label_bg_color": self.label_bg_color,
                    "label_fg_color": self.label_fg_color,
                    "threshold_color_low": self.threshold_color_low,
                    "threshold_color_medium": self.threshold_color_medium,
                    "threshold_color_high": self.threshold_color_high,
                    "usage_basis": self.usage_basis,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
