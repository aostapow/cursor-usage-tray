from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

import requests

USAGE_SUMMARY_URL = "https://cursor.com/api/usage-summary"
USAGE_EVENTS_URL = "https://cursor.com/api/dashboard/get-filtered-usage-events"
DASHBOARD_URL = "https://cursor.com/dashboard/usage"
DEFAULT_PAGE_SIZE = 100


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
    cycle_tokens: Optional[int]
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
        if self.cycle_tokens is not None:
            lines.append(f"Tokens ciclo: {self.cycle_tokens:,}".replace(",", "."))
        lines.append(f"Ciclo hasta: {self.billing_cycle_end[:10] if self.billing_cycle_end else '?'}")
        return "\n".join(lines)


def _iso_to_ms(value: str) -> int | None:
    if not value:
        return None
    text = value.strip()
    if text.isdigit():
        return int(text)
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp() * 1000)
    except ValueError:
        return None


def _extract_usage_events(data: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("usageEventsDisplay", "usageEvents", "events"):
        events = data.get(key)
        if isinstance(events, list):
            return [event for event in events if isinstance(event, dict)]
    return []


def _event_tokens(event: dict[str, Any]) -> int:
    usage = event.get("tokenUsage") or {}
    total = 0
    for key in ("inputTokens", "outputTokens", "cacheWriteTokens", "cacheReadTokens"):
        value = usage.get(key)
        if isinstance(value, (int, float)):
            total += int(value)
    return total


class CursorUsageClient:
    def __init__(self, session_token: str) -> None:
        self._session = requests.Session()
        self._session.cookies.set("WorkosCursorSessionToken", session_token, domain="cursor.com")
        self._session.headers.update(
            {
                "User-Agent": "cursor-usage-tray/1.1",
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Origin": "https://cursor.com",
                "Referer": "https://cursor.com/dashboard/usage",
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
            cycle_tokens=None,
            raw=data,
        )

    def fetch_cycle_tokens(self, snapshot: UsageSnapshot) -> int | None:
        start_ms = _iso_to_ms(snapshot.billing_cycle_start)
        end_ms = _iso_to_ms(snapshot.billing_cycle_end)
        if start_ms is None or end_ms is None:
            return None

        total_tokens = 0
        fetched_events = 0
        expected_total = 0
        page = 1
        while True:
            payload = {
                "startDate": str(start_ms),
                "endDate": str(end_ms),
                "page": page,
                "pageSize": DEFAULT_PAGE_SIZE,
            }
            response = self._session.post(USAGE_EVENTS_URL, json=payload, timeout=30)
            if response.status_code in (401, 403):
                raise PermissionError("Token inválido o sin permiso para eventos de uso.")
            response.raise_for_status()
            data = response.json()
            if page == 1:
                expected_total = int(data.get("totalUsageEventsCount") or 0)
            events = _extract_usage_events(data)
            if not events:
                break
            for event in events:
                total_tokens += _event_tokens(event)
            fetched_events += len(events)

            pagination = data.get("pagination") or {}
            has_next = pagination.get("hasNextPage")
            if has_next is False:
                break
            if expected_total and fetched_events >= expected_total:
                break
            if len(events) < DEFAULT_PAGE_SIZE:
                break
            page += 1
            if page > 500:
                break

        if expected_total > 0 and fetched_events == 0:
            return None
        return total_tokens

    def fetch_snapshot_with_tokens(self, *, include_tokens: bool) -> UsageSnapshot:
        snapshot = self.fetch_usage_summary()
        if not include_tokens:
            return snapshot
        try:
            tokens = self.fetch_cycle_tokens(snapshot)
        except Exception:  # noqa: BLE001
            tokens = None
        return UsageSnapshot(
            membership_type=snapshot.membership_type,
            billing_cycle_start=snapshot.billing_cycle_start,
            billing_cycle_end=snapshot.billing_cycle_end,
            on_demand_usd=snapshot.on_demand_usd,
            on_demand_limit_usd=snapshot.on_demand_limit_usd,
            plan_used=snapshot.plan_used,
            plan_limit=snapshot.plan_limit,
            plan_percent_used=snapshot.plan_percent_used,
            cycle_tokens=tokens,
            raw=snapshot.raw,
        )
