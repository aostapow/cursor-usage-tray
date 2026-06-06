from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from .usage_levels import DEFAULT_THRESHOLD_GREEN_MAX, DEFAULT_THRESHOLD_YELLOW_MAX, UsageThresholds

APP_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "cursor-usage-tray"
CONFIG_PATH = APP_DIR / "config.json"
DEFAULT_REFRESH_SECONDS = 120


@dataclass
class AppConfig:
    refresh_interval_seconds: int = DEFAULT_REFRESH_SECONDS
    display_mode: str = "on_demand_usd"
    open_dashboard_on_click: bool = False
    show_taskbar_label: bool = True
    show_tray_icon: bool = True
    start_with_windows: bool = False
    label_x: int | None = None
    label_y: int | None = None
    threshold_green_max: float = DEFAULT_THRESHOLD_GREEN_MAX
    threshold_yellow_max: float = DEFAULT_THRESHOLD_YELLOW_MAX

    def usage_thresholds(self) -> UsageThresholds:
        return UsageThresholds(
            green_max=self.threshold_green_max,
            yellow_max=self.threshold_yellow_max,
        ).normalized()

    @classmethod
    def load(cls) -> "AppConfig":
        if not CONFIG_PATH.exists():
            return cls()
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        label_x = data.get("label_x")
        label_y = data.get("label_y")
        config = cls(
            refresh_interval_seconds=max(60, int(data.get("refresh_interval_seconds", DEFAULT_REFRESH_SECONDS))),
            display_mode=str(data.get("display_mode", "on_demand_usd")),
            open_dashboard_on_click=bool(data.get("open_dashboard_on_click", False)),
            show_taskbar_label=bool(data.get("show_taskbar_label", True)),
            show_tray_icon=True,
            start_with_windows=bool(data.get("start_with_windows", False)),
            label_x=int(label_x) if label_x is not None else None,
            label_y=int(label_y) if label_y is not None else None,
            threshold_green_max=float(data.get("threshold_green_max", DEFAULT_THRESHOLD_GREEN_MAX)),
            threshold_yellow_max=float(data.get("threshold_yellow_max", DEFAULT_THRESHOLD_YELLOW_MAX)),
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
                    "show_taskbar_label": self.show_taskbar_label,
                    "show_tray_icon": self.show_tray_icon,
                    "start_with_windows": self.start_with_windows,
                    "label_x": self.label_x,
                    "label_y": self.label_y,
                    "threshold_green_max": thresholds.green_max,
                    "threshold_yellow_max": thresholds.yellow_max,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
