from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .api import UsageSnapshot
    from .config import AppConfig


class LabelMode(str, Enum):
    USD = "usd"
    TOKENS = "tokens"
    PLAN = "plan"


@dataclass(frozen=True)
class LabelDisplay:
    text: str
    mode: LabelMode
    amount_usd: float | None
    use_threshold_colors: bool


def format_tokens(count: int | None) -> str:
    if count is None:
        return "— tok"
    if count >= 1_000_000:
        value = count / 1_000_000
        return f"{value:.1f}M tok".replace(".0M", "M")
    if count >= 10_000:
        value = count / 1_000
        return f"{value:.1f}K tok".replace(".0K", "K")
    return f"{count:,} tok".replace(",", ".")


def format_plan(snapshot: "UsageSnapshot") -> str:
    if snapshot.plan_percent_used is not None:
        return f"{snapshot.plan_percent_used:.0f}%"
    if snapshot.plan_used is not None and snapshot.plan_limit is not None:
        return f"{snapshot.plan_used}/{snapshot.plan_limit}"
    return "—%"


def enabled_modes(config: "AppConfig", snapshot: "UsageSnapshot | None") -> list[LabelMode]:
    modes: list[LabelMode] = []
    if config.label_show_usd:
        modes.append(LabelMode.USD)
    if config.label_show_tokens:
        if snapshot is None or snapshot.cycle_tokens is not None:
            modes.append(LabelMode.TOKENS)
    if config.label_show_plan:
        modes.append(LabelMode.PLAN)
    if not modes:
        modes.append(LabelMode.USD)
    return modes


def display_for_mode(mode: LabelMode, snapshot: "UsageSnapshot | None", *, error: bool) -> LabelDisplay:
    if error or snapshot is None:
        if mode == LabelMode.USD:
            return LabelDisplay("$!", LabelMode.USD, None, True)
        if mode == LabelMode.TOKENS:
            return LabelDisplay("— tok", LabelMode.TOKENS, None, False)
        return LabelDisplay("—%", LabelMode.PLAN, None, False)

    if mode == LabelMode.USD:
        return LabelDisplay(
            snapshot.label_short,
            LabelMode.USD,
            snapshot.on_demand_usd,
            True,
        )
    if mode == LabelMode.TOKENS:
        return LabelDisplay(
            format_tokens(snapshot.cycle_tokens),
            LabelMode.TOKENS,
            None,
            False,
        )
    return LabelDisplay(
        format_plan(snapshot),
        LabelMode.PLAN,
        None,
        False,
    )


def current_display(
    config: "AppConfig",
    snapshot: "UsageSnapshot | None",
    *,
    mode_index: int,
    error: bool,
) -> LabelDisplay:
    modes = enabled_modes(config, snapshot)
    if not modes:
        return LabelDisplay("$-.--", LabelMode.USD, None, True)
    if config.label_alternate_seconds <= 0:
        mode_index = 0
    mode = modes[mode_index % len(modes)]
    return display_for_mode(mode, snapshot, error=error)
