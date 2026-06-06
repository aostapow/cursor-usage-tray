from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import requests

USAGE_SUMMARY_URL = "https://cursor.com/api/usage-summary"
DASHBOARD_URL = "https://cursor.com/dashboard/usage"


@dataclass
class UsageSnapshot:
    membership_type: str
    billing_cycle_start: str
    billing_cycle_end: str
    on_demand_usd: float
    on_demand_limit_usd: Optional[float]
    plan_used: Optional[int]
    plan_limit: Optional[int]
    plan_percent_used: Optional[float]
    raw: dict[str, Any]

    @property
    def label_short(self) -> str:
        return f"${self.on_demand_usd:.2f}"

    @property
    def tooltip(self) -> str:
        lines = [
            f"Plan: {self.membership_type or 'unknown'}",
            f"On-demand: ${self.on_demand_usd:.2f}",
        ]
        if self.on_demand_limit_usd is not None:
            lines.append(f"Límite on-demand: ${self.on_demand_limit_usd:.2f}")
        if self.plan_limit is not None and self.plan_used is not None:
            lines.append(f"Incluido: {self.plan_used}/{self.plan_limit}")
        if self.plan_percent_used is not None:
            lines.append(f"Uso plan: {self.plan_percent_used:.0f}%")
        lines.append(f"Ciclo hasta: {self.billing_cycle_end[:10] if self.billing_cycle_end else '?'}")
        return "\n".join(lines)


class CursorUsageClient:
    def __init__(self, session_token: str) -> None:
        self._session = requests.Session()
        self._session.cookies.set("WorkosCursorSessionToken", session_token, domain="cursor.com")
        self._session.headers.update(
            {
                "User-Agent": "cursor-usage-tray/0.1",
                "Accept": "application/json",
            }
        )

    def fetch_usage_summary(self) -> UsageSnapshot:
        response = self._session.get(USAGE_SUMMARY_URL, timeout=20)
        if response.status_code == 401:
            raise PermissionError("Token inválido o expirado (401). Renová WorkosCursorSessionToken.")
        response.raise_for_status()
        data = response.json()

        individual = data.get("individualUsage") or {}
        plan = individual.get("plan") or {}
        on_demand = individual.get("onDemand") or {}
        team_on_demand = (data.get("teamUsage") or {}).get("onDemand") or {}

        on_demand_cents = on_demand.get("used")
        if on_demand_cents is None and team_on_demand.get("used") is not None:
            on_demand_cents = team_on_demand.get("used")

        limit_cents = on_demand.get("limit")
        if limit_cents is None:
            limit_cents = team_on_demand.get("limit")

        return UsageSnapshot(
            membership_type=str(data.get("membershipType") or ""),
            billing_cycle_start=str(data.get("billingCycleStart") or ""),
            billing_cycle_end=str(data.get("billingCycleEnd") or ""),
            on_demand_usd=(float(on_demand_cents or 0) / 100.0),
            on_demand_limit_usd=(float(limit_cents) / 100.0 if limit_cents is not None else None),
            plan_used=plan.get("used"),
            plan_limit=plan.get("limit"),
            plan_percent_used=plan.get("totalPercentUsed"),
            raw=data,
        )
