from __future__ import annotations

from dataclasses import dataclass
import time
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
    included_usd: float
    included_limit_usd: Optional[float]
    on_demand_limit_usd: Optional[float]
    team_on_demand_usd: Optional[float]
    team_on_demand_limit_usd: Optional[float]
    plan_used: Optional[int]
    plan_limit: Optional[int]
    plan_percent_used: Optional[float]
    cycle_tokens: Optional[int]
    daily_tokens: Optional[int]
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
        if self.included_usd > 0:
            lines.append(f"Incluido (USD): ${self.included_usd:.2f}")
        if self.plan_percent_used is not None:
            lines.append(f"Uso plan: {self.plan_percent_used:.0f}%")
        if self.cycle_tokens is not None:
            lines.append(f"Tokens ciclo: {self.cycle_tokens:,}".replace(",", "."))
        if self.daily_tokens is not None:
            lines.append(f"Tokens hoy: {self.daily_tokens:,}".replace(",", "."))
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


def _extract_included_usd(plan: dict[str, Any]) -> float:
    if not plan:
        return 0.0
    for key in ("spent", "used", "usedSpend", "totalSpend", "spentUsd", "usedUsd"):
        raw = plan.get(key)
        if raw is None:
            continue
        value = float(raw)
        return value / 100.0 if value > 500 else value
    for key in ("spentCents", "usedCents"):
        raw = plan.get(key)
        if raw is not None:
            return float(raw) / 100.0
    return 0.0


def _extract_included_limit_usd(plan: dict[str, Any]) -> float | None:
    if not plan:
        return None
    for key in ("limit", "spendLimit", "totalLimit", "limitUsd", "includedLimitUsd"):
        raw = plan.get(key)
        if raw is None:
            continue
        value = float(raw)
        return value / 100.0 if value > 500 else value
    for key in ("limitCents", "spendLimitCents", "includedLimitCents"):
        raw = plan.get(key)
        if raw is not None:
            return float(raw) / 100.0
    return None


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

        team_used_cents = team_on_demand.get("used")
        team_limit_cents = team_on_demand.get("limit")

        return UsageSnapshot(
            membership_type=str(data.get("membershipType") or ""),
            billing_cycle_start=str(data.get("billingCycleStart") or ""),
            billing_cycle_end=str(data.get("billingCycleEnd") or ""),
            on_demand_usd=(float(on_demand_cents or 0) / 100.0),
            included_usd=_extract_included_usd(plan),
            included_limit_usd=_extract_included_limit_usd(plan),
            on_demand_limit_usd=(float(limit_cents) / 100.0 if limit_cents is not None else None),
            team_on_demand_usd=(
                float(team_used_cents) / 100.0 if team_used_cents is not None else None
            ),
            team_on_demand_limit_usd=(
                float(team_limit_cents) / 100.0 if team_limit_cents is not None else None
            ),
            plan_used=plan.get("used"),
            plan_limit=plan.get("limit"),
            plan_percent_used=plan.get("totalPercentUsed"),
            cycle_tokens=None,
            daily_tokens=None,
            raw=data,
        )

    def _fetch_tokens_in_range(self, start_ms: int, end_ms: int) -> int | None:
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

    def fetch_cycle_tokens(self, snapshot: UsageSnapshot) -> int | None:
        start_ms = _iso_to_ms(snapshot.billing_cycle_start)
        end_ms = _iso_to_ms(snapshot.billing_cycle_end)
        if start_ms is None or end_ms is None:
            return None
        return self._fetch_tokens_in_range(start_ms, end_ms)

    def fetch_daily_tokens(self) -> int | None:
        now = datetime.now().astimezone()
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        start_ms = int(start.timestamp() * 1000)
        end_ms = int(time.time() * 1000)
        return self._fetch_tokens_in_range(start_ms, end_ms)

    def fetch_snapshot_with_tokens(
        self,
        *,
        include_cycle_tokens: bool,
        include_daily_tokens: bool,
    ) -> UsageSnapshot:
        snapshot = self.fetch_usage_summary()
        cycle_tokens = snapshot.cycle_tokens
        daily_tokens = snapshot.daily_tokens
        if include_cycle_tokens:
            try:
                cycle_tokens = self.fetch_cycle_tokens(snapshot)
            except Exception:  # noqa: BLE001
                cycle_tokens = None
        if include_daily_tokens:
            try:
                daily_tokens = self.fetch_daily_tokens()
            except Exception:  # noqa: BLE001
                daily_tokens = None
        return UsageSnapshot(
            membership_type=snapshot.membership_type,
            billing_cycle_start=snapshot.billing_cycle_start,
            billing_cycle_end=snapshot.billing_cycle_end,
            on_demand_usd=snapshot.on_demand_usd,
            included_usd=snapshot.included_usd,
            included_limit_usd=snapshot.included_limit_usd,
            on_demand_limit_usd=snapshot.on_demand_limit_usd,
            team_on_demand_usd=snapshot.team_on_demand_usd,
            team_on_demand_limit_usd=snapshot.team_on_demand_limit_usd,
            plan_used=snapshot.plan_used,
            plan_limit=snapshot.plan_limit,
            plan_percent_used=snapshot.plan_percent_used,
            cycle_tokens=cycle_tokens,
            daily_tokens=daily_tokens,
            raw=snapshot.raw,
        )
