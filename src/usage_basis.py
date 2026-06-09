from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .api import UsageSnapshot


class UsageBasis(str, Enum):
    INCLUDED = "included"
    ON_DEMAND = "on_demand"
    AUTO = "auto"

    @classmethod
    def parse(cls, value: str | None) -> "UsageBasis":
        if value == "both":
            return cls.AUTO
        if value in {item.value for item in cls}:
            return cls(str(value))
        return cls.ON_DEMAND


def included_percent(snapshot: "UsageSnapshot") -> float:
    if snapshot.included_limit_usd is not None and snapshot.included_limit_usd > 0:
        return min(100.0, (included_usd_amount(snapshot) / snapshot.included_limit_usd) * 100.0)
    if snapshot.plan_percent_used is not None:
        return float(snapshot.plan_percent_used)
    if snapshot.plan_used is not None and snapshot.plan_limit and snapshot.plan_limit > 0:
        return (float(snapshot.plan_used) / float(snapshot.plan_limit)) * 100.0
    return 0.0


def included_usd_amount(snapshot: "UsageSnapshot") -> float:
    if snapshot.included_usd > 0:
        return snapshot.included_usd
    return 0.0


def included_at_max(snapshot: "UsageSnapshot") -> bool:
    return included_percent(snapshot) >= 100.0


def on_demand_used_usd(snapshot: "UsageSnapshot") -> float:
    if snapshot.team_on_demand_usd is not None:
        return snapshot.team_on_demand_usd
    return snapshot.on_demand_usd


def on_demand_limit_usd(snapshot: "UsageSnapshot") -> float | None:
    if snapshot.team_on_demand_limit_usd is not None:
        return snapshot.team_on_demand_limit_usd
    return snapshot.on_demand_limit_usd


def on_demand_percent(snapshot: "UsageSnapshot") -> float:
    limit = on_demand_limit_usd(snapshot)
    if limit is None or limit <= 0:
        return 0.0
    used = on_demand_used_usd(snapshot)
    return min(100.0, (used / limit) * 100.0)


def effective_basis(snapshot: "UsageSnapshot | None", basis: UsageBasis) -> UsageBasis:
    if snapshot is None:
        return UsageBasis.ON_DEMAND if basis == UsageBasis.AUTO else basis
    if basis != UsageBasis.AUTO:
        return basis
    if included_at_max(snapshot):
        return UsageBasis.ON_DEMAND
    return UsageBasis.INCLUDED


def usage_percent(snapshot: "UsageSnapshot | None", basis: UsageBasis) -> float | None:
    if snapshot is None:
        return None
    resolved = effective_basis(snapshot, basis)
    if resolved == UsageBasis.INCLUDED:
        return included_percent(snapshot)
    return on_demand_percent(snapshot)


def basis_usd_amount(snapshot: "UsageSnapshot | None", basis: UsageBasis) -> float | None:
    if snapshot is None:
        return None
    resolved = effective_basis(snapshot, basis)
    if resolved == UsageBasis.INCLUDED:
        return included_usd_amount(snapshot)
    return on_demand_used_usd(snapshot)


def basis_percent_label(snapshot: "UsageSnapshot | None", basis: UsageBasis) -> str:
    pct = usage_percent(snapshot, basis)
    if pct is None:
        return "—%"
    return f"{pct:.0f}%"


def basis_usd_label(snapshot: "UsageSnapshot | None", basis: UsageBasis) -> str:
    amount = basis_usd_amount(snapshot, basis)
    if amount is None:
        return "$-.--"
    return f"${amount:.2f}"


# Alias: percent for threshold coloring in legacy callers.
def basis_amount(snapshot: "UsageSnapshot | None", basis: UsageBasis) -> float | None:
    return usage_percent(snapshot, basis)
