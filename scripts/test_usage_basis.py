"""Unit tests for usage basis calculations."""

from __future__ import annotations



import sys

from pathlib import Path



ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(ROOT))



from src.api import UsageSnapshot  # noqa: E402

from src.usage_basis import (  # noqa: E402
    UsageBasis,
    basis_percent_label,
    basis_usd_label,
    effective_basis,
    included_at_max,
    usage_percent,
)





def _snapshot(

    *,

    on_demand: float = 5.0,

    on_demand_limit: float | None = 50.0,

    team_on_demand: float | None = 10.0,

    team_on_demand_limit: float | None = 100.0,

    included: float = 0.0,
    included_limit: float | None = None,

    percent: float | None = 40.0,

    plan_used: int | None = 100,

    plan_limit: int | None = 500,

) -> UsageSnapshot:

    return UsageSnapshot(

        membership_type="pro",

        billing_cycle_start="2026-01-01",

        billing_cycle_end="2026-02-01",

        on_demand_usd=on_demand,

        included_usd=included,

        included_limit_usd=included_limit,

        on_demand_limit_usd=on_demand_limit,

        team_on_demand_usd=team_on_demand,

        team_on_demand_limit_usd=team_on_demand_limit,

        plan_used=plan_used,

        plan_limit=plan_limit,

        plan_percent_used=percent,

        cycle_tokens=None,

        daily_tokens=None,

        raw={},

    )





def test_on_demand_percent_uses_team_limit() -> None:
    snap = _snapshot(team_on_demand=25.0, team_on_demand_limit=100.0)
    assert usage_percent(snap, UsageBasis.ON_DEMAND) == 25.0
    assert basis_percent_label(snap, UsageBasis.ON_DEMAND) == "25%"
    assert basis_usd_label(snap, UsageBasis.ON_DEMAND) == "$25.00"





def test_included_percent() -> None:
    snap = _snapshot(percent=42.0, included=10.61, included_limit=20.0)
    assert round(usage_percent(snap, UsageBasis.INCLUDED), 2) == 53.05
    assert basis_percent_label(snap, UsageBasis.INCLUDED) == "53%"
    assert basis_usd_label(snap, UsageBasis.INCLUDED) == "$10.61"





def test_auto_before_included_max() -> None:

    snap = _snapshot(percent=80.0, team_on_demand=50.0)

    assert effective_basis(snap, UsageBasis.AUTO) == UsageBasis.INCLUDED

    assert usage_percent(snap, UsageBasis.AUTO) == 80.0





def test_auto_after_included_max() -> None:

    snap = _snapshot(percent=100.0, team_on_demand=30.0, team_on_demand_limit=100.0)

    assert included_at_max(snap)

    assert effective_basis(snap, UsageBasis.AUTO) == UsageBasis.ON_DEMAND

    assert usage_percent(snap, UsageBasis.AUTO) == 30.0





def test_both_config_migrates_to_auto() -> None:

    assert UsageBasis.parse("both") == UsageBasis.AUTO





def main() -> int:

    test_on_demand_percent_uses_team_limit()

    test_included_percent()

    test_auto_before_included_max()

    test_auto_after_included_max()

    test_both_config_migrates_to_auto()

    print("OK: all usage basis tests passed")

    return 0





if __name__ == "__main__":

    raise SystemExit(main())


