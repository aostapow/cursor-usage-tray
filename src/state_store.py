from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from typing import Any

from .paths import STATE_PATH


@dataclass
class AppState:
    on_demand_usd: float | None = None
    membership_type: str = ""
    tray_tip: str = "Cursor usage"
    tooltip: str = "Cursor usage"
    has_error: bool = False
    updated_at: float = 0.0
    float_version: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AppState":
        return cls(
            on_demand_usd=data.get("on_demand_usd"),
            membership_type=str(data.get("membership_type") or ""),
            tray_tip=str(data.get("tray_tip") or "Cursor usage"),
            tooltip=str(data.get("tooltip") or "Cursor usage"),
            has_error=bool(data.get("has_error")),
            updated_at=float(data.get("updated_at") or 0.0),
            float_version=str(data.get("float_version") or ""),
        )


def write_state(state: AppState) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = state.to_dict()
    payload["updated_at"] = time.time()
    STATE_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def read_state() -> AppState | None:
    if not STATE_PATH.exists():
        return None
    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return AppState.from_dict(data)
    except (json.JSONDecodeError, OSError, TypeError, ValueError):
        pass
    return None
