from __future__ import annotations



from dataclasses import dataclass

from enum import Enum





class UsageLevel(str, Enum):

    LOW = "low"

    MEDIUM = "medium"

    HIGH = "high"

    UNKNOWN = "unknown"





DEFAULT_THRESHOLD_GREEN_MAX = 15.0

DEFAULT_THRESHOLD_YELLOW_MAX = 20.0





@dataclass(frozen=True)

class UsageThresholds:

    green_max: float = DEFAULT_THRESHOLD_GREEN_MAX

    yellow_max: float = DEFAULT_THRESHOLD_YELLOW_MAX



    def normalized(self) -> "UsageThresholds":

        green = max(0.0, float(self.green_max))

        yellow = max(green, float(self.yellow_max))

        return UsageThresholds(green_max=green, yellow_max=yellow)





@dataclass(frozen=True)

class UsageStyle:

    level: UsageLevel

    fg: str

    bg: str

    accent: str





_STYLES = {

    UsageLevel.LOW: UsageStyle(UsageLevel.LOW, "#9ef0a5", "#1a3d22", "#22c55e"),

    UsageLevel.MEDIUM: UsageStyle(UsageLevel.MEDIUM, "#ffe08a", "#4a3b12", "#eab308"),

    UsageLevel.HIGH: UsageStyle(UsageLevel.HIGH, "#ffb4ab", "#4a1714", "#ef4444"),

    UsageLevel.UNKNOWN: UsageStyle(UsageLevel.UNKNOWN, "#d4d4d8", "#27272a", "#71717a"),

}





def usage_level(amount_usd: float | None, thresholds: UsageThresholds | None = None) -> UsageLevel:

    if amount_usd is None:

        return UsageLevel.UNKNOWN

    t = (thresholds or UsageThresholds()).normalized()

    if amount_usd < t.green_max:

        return UsageLevel.LOW

    if amount_usd <= t.yellow_max:

        return UsageLevel.MEDIUM

    return UsageLevel.HIGH





def usage_style(amount_usd: float | None, thresholds: UsageThresholds | None = None) -> UsageStyle:

    return _STYLES[usage_level(amount_usd, thresholds)]


